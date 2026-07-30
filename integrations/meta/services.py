"""
integrations/meta/services.py
──────────────────────────────
High-level Meta Pixel + Conversions API service layer.

This is the only module your views/signals need to import.

Usage
-----
    from integrations.meta.services import meta

    # In a view, after form submission:
    event_id = meta.track_lead(
        request,
        lead_type="Inquiry Form",
        country="BD",
        preferred_university="University of Oxford",
        degree="BSc",
        course="Computer Science",
        intake="September 2025",
        value=0,
        currency="BDT",
    )
    # Pass event_id to the template so the frontend JS can deduplicate:
    # fbq('track', 'Lead', {...}, { eventID: '{{ event_id }}' });

Architecture
------------
  - MetaPixelService wraps MetaAPIClient.
  - Each track_* method:
      1. Checks if tracking is enabled.
      2. Generates a unique event_id.
      3. Builds the user_data dict (hashed PII + network signals).
      4. Assembles the CAPI event payload.
      5. Calls client.send_event() (fire-and-forget, never raises).
      6. Returns the event_id for frontend deduplication.

Education Consultancy Context
------------------------------
The helper methods map exactly to the lead-generation events described
in the requirements: Lead, ViewContent, Search, Contact, Schedule,
SubmitApplication, Purchase, CompleteRegistration, PageView.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from django.conf import settings
from django.http import HttpRequest

from .client import MetaAPIClient
from .utils import build_user_data, generate_event_id, get_client_ip, get_client_user_agent

logger = logging.getLogger("integrations.meta")


class MetaPixelService:
    """
    Singleton-style service for sending Meta Pixel / CAPI events.

    The service is automatically disabled (all methods are safe no-ops)
    when META_PIXEL_ID is not configured.
    """

    def __init__(self) -> None:
        self._client = MetaAPIClient()
        self._enabled: bool = bool(getattr(settings, "META_PIXEL_ID", ""))

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _build_event(
        self,
        request: HttpRequest,
        event_name: str,
        custom_data: Optional[dict] = None,
        user_data_kwargs: Optional[dict] = None,
        event_id: Optional[str] = None,
    ) -> tuple[str, dict]:
        """
        Construct a complete CAPI event dict.

        Returns (event_id, event_dict).
        """
        event_id = event_id or generate_event_id()
        ts = int(time.time())

        user_data = build_user_data(request, **(user_data_kwargs or {}))

        event: dict = {
            "event_name": event_name,
            "event_time": ts,
            "event_id": event_id,
            "action_source": "website",
            "event_source_url": request.build_absolute_uri(),
            "user_data": user_data,
        }
        if custom_data:
            event["custom_data"] = {k: v for k, v in custom_data.items() if v is not None}

        return event_id, event

    def _send(
        self,
        request: HttpRequest,
        event_name: str,
        custom_data: Optional[dict] = None,
        user_data_kwargs: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Build and dispatch an event. Returns the event_id on success, None if disabled.
        This method never raises — all exceptions are handled inside the client.
        """
        if not self._enabled:
            return None

        event_id, event = self._build_event(
            request, event_name, custom_data, user_data_kwargs
        )
        self._client.send_event(event)
        return event_id

    # ──────────────────────────────────────────────────────────────────────────
    # Standard events
    # ──────────────────────────────────────────────────────────────────────────

    def track_page_view(self, request: HttpRequest) -> Optional[str]:
        """
        Send a PageView event.

        This is usually fired server-side for the first visit so Meta has a
        reliable baseline even without browser cookies.
        """
        return self._send(request, "PageView")

    def track_view_content(
        self,
        request: HttpRequest,
        *,
        content_name: str = "",
        content_category: str = "University",
        country: str = "",
        degree: str = "",
        content_ids: Optional[list] = None,
    ) -> Optional[str]:
        """
        ViewContent — fired when a user views a university / course page.

        Parameters
        ----------
        content_name      : University or course name
        content_category  : "University" | "Course" | "Program"
        country           : Destination country (e.g. "United Kingdom")
        degree            : "BSc" | "MSc" | "PhD" | "Diploma" etc.
        content_ids       : Optional list of content IDs
        """
        custom_data = {
            "content_name": content_name,
            "content_category": content_category,
            "country": country,
            "degree": degree,
        }
        if content_ids:
            custom_data["content_ids"] = content_ids
        return self._send(request, "ViewContent", custom_data)

    def track_search(
        self,
        request: HttpRequest,
        *,
        search_string: str = "",
        country: str = "",
        degree: str = "",
    ) -> Optional[str]:
        """
        Search — fired when a user runs a university/course search.

        Parameters
        ----------
        search_string : The raw search query
        country       : Destination country filter
        degree        : Degree type filter
        """
        custom_data = {
            "search_string": search_string,
            "country": country,
            "degree": degree,
        }
        return self._send(request, "Search", custom_data)

    def track_contact(
        self,
        request: HttpRequest,
        *,
        contact_method: str = "",
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[str]:
        """
        Contact — fired when a user initiates contact.

        Trigger scenarios: WhatsApp click, phone call tap, Messenger,
        or Contact Form submission.

        Parameters
        ----------
        contact_method : "WhatsApp" | "Call" | "Messenger" | "Contact Form"
        email / phone  : Optional PII for user_data (will be hashed)
        """
        custom_data = {"contact_method": contact_method}
        user_data_kwargs = {"email": email, "phone": phone}
        return self._send(request, "Contact", custom_data, user_data_kwargs)

    def track_lead(
        self,
        request: HttpRequest,
        *,
        lead_type: str = "",
        country: str = "",
        preferred_university: str = "",
        degree: str = "",
        course: str = "",
        intake: str = "",
        value: float = 0.0,
        currency: str = "BDT",
        email: Optional[str] = None,
        phone: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Lead — fired on any lead-generation action.

        Trigger scenarios:
          • Inquiry Form submission
          • Contact Form submission
          • "Apply Now" button click
          • WhatsApp Lead

        Parameters
        ----------
        lead_type           : "Inquiry Form" | "Contact Form" | "Apply Now" | "WhatsApp Lead"
        country             : Desired study-abroad destination
        preferred_university: Target university name
        degree              : Degree level
        course              : Specific course / programme name
        intake              : Intake period (e.g. "September 2025")
        value               : Estimated lead value (default 0)
        currency            : ISO 4217 currency code (default "BDT")
        email / phone / name: Optional PII — hashed automatically
        """
        custom_data = {
            "lead_type": lead_type,
            "country": country,
            "preferred_university": preferred_university,
            "degree": degree,
            "course": course,
            "intake": intake,
            "value": value,
            "currency": currency.upper(),
        }
        user_data_kwargs = {
            "email": email,
            "phone": phone,
            "first_name": first_name,
            "last_name": last_name,
        }
        return self._send(request, "Lead", custom_data, user_data_kwargs)

    def track_schedule(
        self,
        request: HttpRequest,
        *,
        consultant: str = "",
        appointment_date: str = "",
        country: str = "",
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[str]:
        """
        Schedule — fired when a consultation appointment is booked.

        Parameters
        ----------
        consultant       : Name / ID of the assigned consultant
        appointment_date : ISO 8601 date string (e.g. "2025-09-15")
        country          : Study destination country
        """
        custom_data = {
            "consultant": consultant,
            "appointment_date": appointment_date,
            "country": country,
        }
        user_data_kwargs = {"email": email, "phone": phone}
        return self._send(request, "Schedule", custom_data, user_data_kwargs)

    def track_submit_application(
        self,
        request: HttpRequest,
        *,
        application_id: str = "",
        country: str = "",
        university: str = "",
        course: str = "",
        degree: str = "",
        intake: str = "",
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[str]:
        """
        SubmitApplication — fired when a student submits a university application.

        Parameters
        ----------
        application_id : Internal application reference number
        country        : Destination country
        university     : Applied university name
        course         : Applied course / programme
        degree         : Degree level
        intake         : Intake session
        """
        custom_data = {
            "application_id": application_id,
            "country": country,
            "university": university,
            "course": course,
            "degree": degree,
            "intake": intake,
        }
        user_data_kwargs = {"email": email, "phone": phone}
        return self._send(request, "SubmitApplication", custom_data, user_data_kwargs)

    def track_purchase(
        self,
        request: HttpRequest,
        *,
        order_id: str = "",
        value: float = 0.0,
        currency: str = "BDT",
        service_name: str = "",
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[str]:
        """
        Purchase — fired when a payment completes successfully.

        Parameters
        ----------
        order_id     : Unique order / transaction reference
        value        : Total payment amount
        currency     : ISO 4217 currency code (default "BDT")
        service_name : Name of the paid service (e.g. "Application Fee")
        """
        custom_data = {
            "order_id": order_id,
            "value": value,
            "currency": currency.upper(),
            "service_name": service_name,
            # Meta requires content_type and contents for Purchase
            "content_type": "product",
            "contents": [
                {"id": order_id, "quantity": 1, "item_price": value}
            ],
        }
        user_data_kwargs = {"email": email, "phone": phone}
        return self._send(request, "Purchase", custom_data, user_data_kwargs)

    def track_complete_registration(
        self,
        request: HttpRequest,
        *,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        CompleteRegistration — fired when a new account is created.
        """
        user_data_kwargs = {
            "email": email,
            "phone": phone,
            "first_name": first_name,
            "last_name": last_name,
        }
        return self._send(request, "CompleteRegistration", None, user_data_kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton — import this in your views
# ─────────────────────────────────────────────────────────────────────────────
meta = MetaPixelService()
