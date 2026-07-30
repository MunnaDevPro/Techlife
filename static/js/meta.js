/**
 * meta.js — Meta Pixel JavaScript Helper
 * ========================================
 * A thin, reusable wrapper around Meta's fbq() function.
 *
 * Features
 * ─────────
 *  • Ensures fbq() is available before calling (safe no-op if pixel not loaded).
 *  • Automatically includes eventID for server-side CAPI deduplication.
 *  • Supports all standard Meta events.
 *  • Zero dependencies — vanilla ES5 for maximum browser compatibility.
 *
 * Usage
 * ─────
 *   // Simple event
 *   Meta.track('PageView');
 *
 *   // Event with parameters (no deduplication)
 *   Meta.track('Search', { search_string: 'Oxford MBA' });
 *
 *   // Event with parameters + deduplication event_id from Django view
 *   Meta.track('Lead', { lead_type: 'Inquiry Form' }, '{{ event_id }}');
 *
 *   // Education consultancy examples
 *   Meta.track('ViewContent', {
 *     content_name: 'University of Oxford',
 *     content_category: 'University',
 *     country: 'United Kingdom',
 *     degree: 'MSc'
 *   });
 *
 *   Meta.track('Purchase', {
 *     value: 5000,
 *     currency: 'BDT',
 *     service_name: 'Application Fee'
 *   }, '{{ event_id }}');
 *
 * Deduplication
 * ─────────────
 * To prevent double-counting between browser Pixel and server-side CAPI:
 *   1. Django view generates a unique event_id and returns it to the template.
 *   2. Template passes event_id to Meta.track().
 *   3. The same event_id is sent via CAPI by Django.
 *   4. Meta deduplicates using the matching event_id.
 *
 * NOTE: This file is only loaded when META_PIXEL_ID is configured (see base.html).
 */

(function (window) {
  'use strict';

  /**
   * @namespace Meta
   */
  var Meta = {

    /**
     * Track a Meta Pixel standard or custom event.
     *
     * @param {string}  eventName  - Standard Meta event name (e.g. 'Lead', 'Purchase').
     * @param {Object}  [params]   - Custom data parameters to send with the event.
     * @param {string}  [eventID]  - Unique event ID for server-side CAPI deduplication.
     *                               Generate this in your Django view using generate_event_id()
     *                               and render it into the template.
     */
    track: function (eventName, params, eventID) {
      if (typeof window.fbq !== 'function') {
        if (window.console && window.console.warn) {
          console.warn('[Meta] fbq() not available. Is the pixel loaded?');
        }
        return;
      }

      params = params || {};
      var options = eventID ? { eventID: eventID } : {};

      try {
        window.fbq('track', eventName, params, options);
      } catch (err) {
        if (window.console && window.console.error) {
          console.error('[Meta] Error tracking event:', eventName, err);
        }
      }
    },

    /**
     * Track a Meta Pixel custom event (non-standard).
     *
     * @param {string}  eventName  - Custom event name.
     * @param {Object}  [params]   - Custom data parameters.
     * @param {string}  [eventID]  - Deduplication event ID.
     */
    trackCustom: function (eventName, params, eventID) {
      if (typeof window.fbq !== 'function') {
        return;
      }
      params = params || {};
      var options = eventID ? { eventID: eventID } : {};
      try {
        window.fbq('trackCustom', eventName, params, options);
      } catch (err) {
        if (window.console && window.console.error) {
          console.error('[Meta] Error tracking custom event:', eventName, err);
        }
      }
    },

    // ─── Convenience helpers ─────────────────────────────────────────────────

    /** Track a PageView event. */
    pageView: function (eventID) {
      this.track('PageView', {}, eventID);
    },

    /**
     * Track a Lead event.
     * @param {Object} params   - { lead_type, country, preferred_university, degree, course, intake }
     * @param {string} eventID  - Deduplication ID from Django CAPI call.
     */
    lead: function (params, eventID) {
      this.track('Lead', params, eventID);
    },

    /**
     * Track a Search event.
     * @param {string} searchString - The search query.
     * @param {Object} [extra]      - Additional params (country, degree).
     * @param {string} [eventID]    - Deduplication ID.
     */
    search: function (searchString, extra, eventID) {
      var params = Object.assign({ search_string: searchString }, extra || {});
      this.track('Search', params, eventID);
    },

    /**
     * Track a ViewContent event.
     * @param {Object} params  - { content_name, content_category, country, degree }
     * @param {string} eventID - Deduplication ID.
     */
    viewContent: function (params, eventID) {
      this.track('ViewContent', params, eventID);
    },

    /**
     * Track a Contact event.
     * @param {string} method  - "WhatsApp" | "Call" | "Messenger" | "Contact Form"
     * @param {string} eventID - Deduplication ID.
     */
    contact: function (method, eventID) {
      this.track('Contact', { contact_method: method }, eventID);
    },

    /**
     * Track a Schedule event (consultation booking).
     * @param {Object} params  - { consultant, appointment_date, country }
     * @param {string} eventID - Deduplication ID.
     */
    schedule: function (params, eventID) {
      this.track('Schedule', params, eventID);
    },

    /**
     * Track a SubmitApplication event.
     * @param {Object} params  - { application_id, country, university, course, degree, intake }
     * @param {string} eventID - Deduplication ID.
     */
    submitApplication: function (params, eventID) {
      this.track('SubmitApplication', params, eventID);
    },

    /**
     * Track a Purchase event (payment success).
     * @param {Object} params  - { value, currency, service_name, order_id }
     * @param {string} eventID - Deduplication ID.
     */
    purchase: function (params, eventID) {
      this.track('Purchase', params, eventID);
    },

    /**
     * Track a CompleteRegistration event (new account created).
     * @param {string} [eventID] - Deduplication ID.
     */
    completeRegistration: function (eventID) {
      this.track('CompleteRegistration', {}, eventID);
    },
  };

  // Expose globally
  window.Meta = Meta;

}(window));
