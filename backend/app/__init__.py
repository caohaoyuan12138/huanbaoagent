from fastapi import APIRouter
from app.db.database import get_db
from app.db.models import Standard, PollutionFactor, PollutionLimit, EnterpriseStandard, Device, DeviceReading, NewsItem, ReportTemplate, ReportInstance

# Import routers (side effects)
from app.routers import knowledge, reports, devices, news, agent  # noqa: F401
