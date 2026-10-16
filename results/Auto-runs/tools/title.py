"""Single source of truth for the article title used by the .docx builders."""
from docx.oxml.ns import qn

TITLE = ("AutoVisco: Physics-Informed Autonomous Rheometry of Liquids, Gels, and Pastes "
         "for Self-Driving Laboratories")


def set_title(paragraph_el):
    """Replace the copied title paragraph's text, keeping its first run's formatting."""
    runs = list(paragraph_el.iter(qn("w:r")))
    texts = [t for r in runs for t in r.iter(qn("w:t"))]
    assert texts and "Rheometer" in "".join(t.text or "" for t in texts), "first front paragraph is not the title"
    texts[0].text = TITLE
    for r in runs:
        if r is not texts[0].getparent():
            r.getparent().remove(r)
