from __future__ import annotations

"""
Unified observation models — page observations, elements, artifacts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.core.models.actions import BoundingBox, BrowserArtifact, SelectorCandidate


class ObservedElement(BaseModel):
    """A single interactive DOM element observed on the page."""
    index: int
    tag: str
    role: Optional[str] = None
    element_type: Optional[str] = None
    text: str = ""
    accessible_name: str = ""
    aria_label: str = ""
    placeholder: str = ""
    name: str = ""
    element_id: str = ""
    href: Optional[str] = None
    value: Optional[str] = None
    visible: bool = False
    enabled: bool = False
    editable: bool = False
    checked: Optional[bool] = None
    bbox: Optional[BoundingBox] = None
    selector_candidates: List[SelectorCandidate] = Field(default_factory=list)
    frame_url: Optional[str] = None
    semantic_type: Optional[str] = None
    visual_description: Optional[str] = None

    @property
    def label(self) -> str:
        parts = [
            self.accessible_name,
            self.aria_label,
            self.text,
            self.placeholder,
            self.name,
            self.element_id,
        ]
        return " ".join(part for part in parts if part).strip()


class Observation(BaseModel):
    """Complete page observation snapshot."""
    url: str
    title: str
    page_type: str
    elements: List[ObservedElement] = Field(default_factory=list)
    forms: List[Dict[str, Any]] = Field(default_factory=list)
    headings: List[str] = Field(default_factory=list)
    page_text: str = ""
    console_errors: List[str] = Field(default_factory=list)
    network_failures: List[str] = Field(default_factory=list)
    dialogs: List[str] = Field(default_factory=list)
    popups: List[str] = Field(default_factory=list)
    iframe_urls: List[str] = Field(default_factory=list)
    viewport: Dict[str, int] = Field(default_factory=dict)
    scroll: Dict[str, float] = Field(default_factory=dict)
    active_element: str = ""
    fingerprint: str = ""
    screenshot: Optional[BrowserArtifact] = None
    screenshot_hash: Optional[str] = None
    dom_hash: Optional[str] = None
    semantic_labels: List[str] = Field(default_factory=list)
    visual_regions: List[Dict[str, Any]] = Field(default_factory=list)
    accessibility_tree_summary: Optional[str] = None
    breadcrumbs: List[str] = Field(default_factory=list)
    active_sidebar_item: str = ""
    loading_indicators: List[str] = Field(default_factory=list)
    visible_tables: List[Dict[str, Any]] = Field(default_factory=list)
    visible_cards: List[Dict[str, Any]] = Field(default_factory=list)
    dashboard_widgets: List[Dict[str, Any]] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def buttons(self) -> List[ObservedElement]:
        return [
            element for element in self.elements
            if element.role == "button" or element.tag == "button"
        ]

    @property
    def links(self) -> List[ObservedElement]:
        return [
            element for element in self.elements
            if element.role == "link" or element.tag == "a"
        ]

    @property
    def inputs(self) -> List[ObservedElement]:
        return [
            element for element in self.elements
            if element.editable or element.tag in {"input", "textarea", "select"}
        ]

    def compact_for_llm(self, limit: int = 80) -> Dict[str, Any]:
        elements = []
        for element in self.elements[:limit]:
            elements.append({
                "index": element.index,
                "role": element.role,
                "tag": element.tag,
                "type": element.element_type,
                "label": element.label,
                "href": element.href,
                "visible": element.visible,
                "enabled": element.enabled,
                "editable": element.editable,
            })
        return {
            "url": self.url,
            "title": self.title,
            "page_type": self.page_type,
            "headings": self.headings[:20],
            "text_excerpt": self.page_text[:4000],
            "console_errors": self.console_errors[-10:],
            "network_failures": self.network_failures[-10:],
            "dialogs": self.dialogs[-5:],
            "popups": self.popups[-5:],
            "viewport": self.viewport,
            "scroll": self.scroll,
            "fingerprint": self.fingerprint,
            "elements": elements,
        }
