from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class AdStatus(str, Enum):
  NEW = "NEW"
  ACTIVE = "ACTIVE"
  INACTIVE = "INACTIVE"


class VisualType(str, Enum):
  PERSON = "PERSON"
  PRODUCT = "PRODUCT"
  TEXT_HEAVY = "TEXT_HEAVY"
  GRAPHIC = "GRAPHIC"


@dataclass
class RawAdItem:
  ad_archive_id: str
  page_id: str
  page_name: str
  copy_text: str
  cta_text: Optional[str]
  image_url: Optional[str]
  format: str  # 'IMAGE', 'VIDEO', 'CAROUSEL'
  start_date: datetime


@dataclass
class ProcessedAdItem:
  ad_archive_id: str
  competitor_id: str
  status: AdStatus
  visual_type: Optional[VisualType]
  first_seen_at: datetime
  last_seen_at: datetime
  consecutive_inactive_days: int = 0


class MetaAdCollectorInterface:

  def extract_page_id(self, ad_library_url: str) -> str:
    """Extracts Meta Page ID from Ad Library URL."""
    raise NotImplementedError

  def fetch_live_ads(self, page_id: str) -> List[RawAdItem]:
    """Fetches raw ad data from Meta Ad Library for a given Page ID."""
    raise NotImplementedError

  def analyze_visual_type(self, image_url: str) -> VisualType:
    """Triggers Vision LLM (e.g., Gemini Vision) to classify image visual type."""
    raise NotImplementedError

  def synchronize_ad_status(
      self,
      competitor_id: str,
      fetched_ads: List[RawAdItem],
      existing_ads: List[Dict],
  ) -> List[ProcessedAdItem]:
    """Calculates status changes (New, Active, Inactive) and updates cumulative survival days."""
    raise NotImplementedError