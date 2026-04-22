"""
Rotational Drag Feedback Controller Helper Module

This module contains the RotationalDragFeedbackController class and related utilities
for automated hit-point detection in viscometer measurements.

Version: 1.0
Module: feedback_helper_function
"""

import math
import statistics
from typing import Dict, List, Optional, Tuple

# Module verification function
def verify_import():

    """Verify that the module has been imported correctly."""
    print("✓ feedback_helper_function v1.0 imported successfully")
    return True


def _mean(values: List[float]) -> float:
    return statistics.mean(values) if values else 0.0


def _std(values: List[float], mean_value: Optional[float] = None) -> float:
    if not values:
        return 0.0
    if mean_value is None:
        mean_value = statistics.mean(values)
    return statistics.pstdev(values, mu=mean_value)


def _linear_regression(x: List[float], y: List[float]) -> Tuple[float, float, float]:
    n = len(x)
    if n == 0:
        return 0.0, 0.0, 0.0
    x_mean = _mean(x)
    y_mean = _mean(y)
    ss_xy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    ss_xx = sum((xi - x_mean) ** 2 for xi in x)
    slope = ss_xy / ss_xx if ss_xx != 0 else 0.0
    intercept = y_mean - slope * x_mean
    y_pred = [slope * xi + intercept for xi in x]
    ss_res = sum((yi - yp) ** 2 for yi, yp in zip(y, y_pred))
    ss_tot = sum((yi - y_mean) ** 2 for yi in y)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
    return slope, intercept, r_squared


def _approximate_second_derivative(z_heights: List[float], drag_values: List[float]) -> Optional[float]:
    if len(z_heights) < 3:
        return None
    x0, x1, x2 = z_heights[-3], z_heights[-2], z_heights[-1]
    y0, y1, y2 = drag_values[-3], drag_values[-2], drag_values[-1]
    if x1 == x0 or x2 == x1 or x2 == x0:
        return None
    return 2 * (((y2 - y1) / (x2 - x1)) - ((y1 - y0) / (x1 - x0))) / (x2 - x0)


class RotationalDragFeedbackController:
    """
    Feedback controller for detecting hit points based on rotational drag trend analysis.
    
    The controller analyzes the trend of Rotational_Drag vs Height_mm for each RPM to detect
    when the viscometer hits the sample surface (hit-point detection).
    """
    
    def __init__(
        self,
        feedback_enabled=True,
        min_data_points=3,
        second_derivative_threshold=-0.5,
        cv_jump_threshold=0.2,
        trend_r_squared_min=0.8,
        hit_point_confidence_threshold=0.6,
        weight_second_derivative=0.5,
        weight_plateau_cv=0.4,
        weight_trend_breakdown=0.3,
        weight_wrong_direction=0.2,
    ):
        self.z_rpm_drag_data = {}  # Structure: {z_height: {rpm: {measurements: [], avg_drag: float}}}
        self.hit_point_detected = False
        self.hit_point_z = None
        self.hit_point_confidence = 0.0
        
        # Configuration parameters
        self.feedback_enabled = feedback_enabled
        self.min_data_points = min_data_points
        self.second_derivative_threshold = second_derivative_threshold
        self.cv_jump_threshold = cv_jump_threshold
        self.trend_r_squared_min = trend_r_squared_min
        self.hit_point_confidence_threshold = hit_point_confidence_threshold
        self.weight_second_derivative = weight_second_derivative
        self.weight_plateau_cv = weight_plateau_cv
        self.weight_trend_breakdown = weight_trend_breakdown
        self.weight_wrong_direction = weight_wrong_direction
        
    def calculate_rotational_drag(self, torque_percent: float, rpm: float) -> float:
        """
        Calculate rotational drag for a single measurement.
        
        Args:
            torque_percent: Torque measurement as percentage
            rpm: RPM at which measurement was taken
            
        Returns:
            Rotational drag = torque_% / RPM
        """
        if rpm == 0:
            return float('inf')  # Avoid division by zero
        return abs(torque_percent) / rpm
    
    def add_measurements_at_z(self, z_height: float, rpm_measurements: Dict[float, List[Dict]]):
        """
        Add torque measurements at a specific Z-height and calculate rotational drag.
        
        Args:
            z_height: Z-position where measurements were taken
            rpm_measurements: Dictionary of {rpm: [measurements]} from viscometer
        """
        if z_height not in self.z_rpm_drag_data:
            self.z_rpm_drag_data[z_height] = {}
        
        for rpm, measurements in rpm_measurements.items():
            if measurements is None:
                continue
                
            # Calculate rotational drag for each measurement
            drag_values = []
            for measurement in measurements:
                torque_percent = measurement.get('torque_percent', 0)
                drag = self.calculate_rotational_drag(torque_percent, rpm)
                drag_values.append(drag)
            
            # Use LATEST rotational drag value instead of average (as requested by user)
            if drag_values:
                latest_drag = drag_values[-1]  # Take the last measurement
                avg_drag = _mean(drag_values)
                cv = _std(drag_values, avg_drag) / avg_drag if avg_drag > 0 else 0
                
                self.z_rpm_drag_data[z_height][rpm] = {
                    'measurements': measurements,
                    'drag_values': drag_values,
                    'avg_drag': avg_drag,
                    'latest_drag': latest_drag,  # Store latest drag value
                    'cv': cv,
                    'num_samples': len(drag_values)
                }
                
                print(f"      RPM {rpm}: Latest Rotational_Drag = {latest_drag:.4f}, Avg = {avg_drag:.4f}, CV = {cv:.3f}")
    
    def analyze_trend_for_rpm(self, rpm: float) -> Dict:
        """
        Analyze the rotational drag trend for a specific RPM across all Z-heights.
        
        Args:
            rpm: RPM to analyze
            
        Returns:
            Dictionary with trend analysis results
        """
        # Get all Z-heights with data for this RPM (sorted from highest to lowest)
        z_heights = []
        drag_values = []
        
        for z_height in sorted(self.z_rpm_drag_data.keys(), reverse=True):
            if rpm in self.z_rpm_drag_data[z_height]:
                z_heights.append(z_height)
                # Use latest drag instead of average as requested by user
                drag_values.append(self.z_rpm_drag_data[z_height][rpm]['latest_drag'])
        
        if len(z_heights) < self.min_data_points:
            return {'valid': False, 'reason': 'insufficient_data'}
        
        # Perform linear regression analysis
        trend_slope, _, trend_r_squared = _linear_regression(z_heights, drag_values)

        # Calculate second derivative approximation if we have enough points
        second_derivative = _approximate_second_derivative(z_heights, drag_values)
        
        # Detect plateau/oscillation behavior using CV analysis
        plateau_score = self._detect_plateau_behavior(rpm, z_heights[-3:] if len(z_heights) >= 3 else z_heights)
        
        # Determine if hit-point is detected
        hit_detected = False
        hit_confidence = 0.0
        hit_reasons = []
        
        # Check for negative second derivative (trend break)
        if second_derivative is not None and second_derivative < self.second_derivative_threshold:
            hit_detected = True
            hit_confidence += self.weight_second_derivative
            hit_reasons.append(f"negative_second_derivative ({second_derivative:.4f})")
        
        # Check for plateau detection
        if plateau_score > self.cv_jump_threshold:
            hit_detected = True
            hit_confidence += self.weight_plateau_cv
            hit_reasons.append(f"plateau_detected ({plateau_score:.3f})")
        
        # Check trend validity (breakdown of linear relationship)
        if trend_r_squared < self.trend_r_squared_min:
            hit_confidence += self.weight_trend_breakdown
            hit_reasons.append(f"trend_breakdown (R²={trend_r_squared:.3f})")
        
        # Check if trend slope is wrong direction (should be negative for normal behavior)
        if trend_slope > 0:  # Positive slope is unusual - drag should increase as Z decreases
            hit_confidence += self.weight_wrong_direction
            hit_reasons.append(f"wrong_trend_direction (slope={trend_slope:.4f})")
            
        # Ensure hit_confidence doesn't exceed 1.0
        hit_confidence = min(hit_confidence, 1.0)
        
        return {
            'valid': True,
            'rpm': rpm,
            'z_heights': z_heights,
            'drag_values': drag_values,
            'trend_slope': trend_slope,
            'trend_r_squared': trend_r_squared,
            'second_derivative': second_derivative,
            'plateau_score': plateau_score,
            'hit_detected': hit_detected,
            'hit_confidence': hit_confidence,
            'hit_reasons': hit_reasons
        }
    
    def _calculate_r_squared(self, x_data: List[float], y_data: List[float], coeffs: List[float]) -> float:
        """Calculate R-squared for linear fit"""
        y_pred = [coeffs[0] * x + coeffs[1] for x in x_data]
        ss_res = sum((y - yp) ** 2 for y, yp in zip(y_data, y_pred))
        y_mean = _mean(y_data)
        ss_tot = sum((y - y_mean) ** 2 for y in y_data)
        return 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    def _detect_plateau_behavior(self, rpm: float, recent_z_heights: List[float]) -> float:
        """
        Detect plateau behavior by analyzing coefficient of variation in recent measurements.
        
        Args:
            rpm: RPM to analyze
            recent_z_heights: List of recent Z-heights to analyze
            
        Returns:
            Plateau score (higher = more likely to be plateau)
        """
        if len(recent_z_heights) < 2:
            return 0.0
        
        # Get all CV values for this RPM across Z-heights
        all_cv_values = []
        recent_cv_values = []
        
        for z_height in sorted(self.z_rpm_drag_data.keys(), reverse=True):
            if z_height in self.z_rpm_drag_data and rpm in self.z_rpm_drag_data[z_height]:
                cv = self.z_rpm_drag_data[z_height][rpm]['cv']
                all_cv_values.append(cv)
                
                if z_height in recent_z_heights:
                    recent_cv_values.append(cv)
        
        if len(recent_cv_values) < 2 or len(all_cv_values) < 4:
            return 0.0
        
        # Calculate baseline CV (average of first 2/3 of measurements)
        baseline_count = max(2, len(all_cv_values) * 2 // 3)
        baseline_cv = _mean(all_cv_values[:baseline_count])
        
        # Calculate recent CV (average of most recent measurements)
        recent_cv = _mean(recent_cv_values)
        
        # Detect jump: recent CV significantly higher than baseline
        if baseline_cv > 0:
            cv_ratio = recent_cv / baseline_cv
            cv_jump = recent_cv - baseline_cv
            
            # Plateau detected if:
            # 1. Recent CV is significantly higher than baseline (ratio > 3)
            # 2. Absolute jump in CV is above threshold
            # 3. Recent CV exceeds absolute threshold (0.15)
            
            plateau_score = 0.0
            if cv_ratio > 3.0 and recent_cv > 0.15:  # 3x increase + high absolute CV
                plateau_score += 0.5
            if cv_jump > self.cv_jump_threshold:  # Absolute jump
                plateau_score += 0.3
            if recent_cv > 0.25:  # Very high recent CV
                plateau_score += 0.2
                
            return min(plateau_score, 1.0)  # Cap at 1.0
        
        return 0.0
    
    def evaluate_hit_point_detection(self, test_rpms: List[float]) -> bool:
        """
        Evaluate if hit point has been detected based on analysis of all RPMs.
        
        Args:
            test_rpms: List of RPMs being tested
            
        Returns:
            True if hit point is detected with sufficient confidence
        """
        if not self.feedback_enabled:
            return False
        
        if len(self.z_rpm_drag_data) < self.min_data_points:
            return False
        
        print(f"    Feedback Controller: Analyzing trends for {len(test_rpms)} RPMs...")
        
        hit_detections = []
        total_confidence = 0.0
        
        # Analyze trend for each RPM
        for rpm in test_rpms:
            trend_analysis = self.analyze_trend_for_rpm(rpm)
            
            if trend_analysis['valid']:
                # Print ALL 3 METRICS clearly as requested by user
                second_deriv_str = f"{trend_analysis['second_derivative']:.4f}" if trend_analysis['second_derivative'] is not None else "N/A"
                print(f"    RPM {rpm} METRICS: 2nd-Derivative = {second_deriv_str}, R² = {trend_analysis['trend_r_squared']:.4f}, CV = {trend_analysis['plateau_score']:.3f}")
                
                if trend_analysis['hit_detected']:
                    hit_detections.append(rpm)
                    total_confidence += trend_analysis['hit_confidence']
                    print(f"    RPM {rpm}: HIT DETECTED (confidence: {trend_analysis['hit_confidence']:.2f}) - {', '.join(trend_analysis['hit_reasons'])}")
                else:
                    print(f"    RPM {rpm}: Normal trend (slope: {trend_analysis['trend_slope']:.4f})")
            else:
                print(f"    RPM {rpm}: {trend_analysis['reason']}")
        
        # Determine overall hit detection
        avg_confidence = total_confidence / len(test_rpms) if len(test_rpms) > 0 else 0
        hit_ratio = len(hit_detections) / len(test_rpms) if len(test_rpms) > 0 else 0
        
        # Hit point detected if:
        # 1. At least 50% of RPMs show hit detection, AND
        # 2. Average confidence exceeds threshold
        if hit_ratio >= 0.5 and avg_confidence >= self.hit_point_confidence_threshold:
            self.hit_point_detected = True
            self.hit_point_confidence = avg_confidence
            
            # Find the Z-height where hit was detected (most recent)
            if self.z_rpm_drag_data:
                self.hit_point_z = min(self.z_rpm_drag_data.keys())  # Most negative Z (lowest point)
            
            print(f"    *** HIT POINT DETECTED *** ")
            print(f"    Hit ratio: {hit_ratio:.1%} ({len(hit_detections)}/{len(test_rpms)} RPMs)")
            print(f"    Confidence: {avg_confidence:.2f}")
            print(f"    Estimated hit Z: {self.hit_point_z:.3f}")
            return True
        else:
            print(f"    No hit point detected (hit ratio: {hit_ratio:.1%}, confidence: {avg_confidence:.2f})")
            return False
    
    def get_summary(self) -> Dict:
        """Get summary of feedback controller analysis"""
        return {
            'hit_point_detected': self.hit_point_detected,
            'hit_point_z': self.hit_point_z,
            'hit_point_confidence': self.hit_point_confidence,
            'total_z_levels': len(self.z_rpm_drag_data),
            'feedback_enabled': self.feedback_enabled
        }