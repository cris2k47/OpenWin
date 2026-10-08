// Override the first run page.
// https://firefox-admin-docs.mozilla.org/reference/policies/overridefirstrunpage/
defaultPref("startup.homepage_welcome_url", "");

// Customize the Firefox Home page.
// https://firefox-admin-docs.mozilla.org/reference/policies/firefoxhome/
defaultPref("browser.newtabpage.activity-stream.showSponsoredTopSites", false);

// Don't display the Firefox Terms of Use and Privacy Notice upon startup.
// https://firefox-admin-docs.mozilla.org/reference/policies/skiptermsofuse/
defaultPref("termsofuse.bypassNotification", true);

// Prevent the upload of telemetry data.
// https://firefox-admin-docs.mozilla.org/reference/policies/disabletelemetry/
defaultPref("datareporting.healthreport.uploadEnabled", false);
defaultPref("datareporting.policy.dataSubmissionEnabled", false);
defaultPref("toolkit.telemetry.archive.enabled", false);
defaultPref("datareporting.usage.uploadEnabled", false);

// Disable the creation of default bookmarks.
// https://firefox-admin-docs.mozilla.org/reference/policies/nodefaultbookmarks/
defaultPref("browser.bookmarks.file", "");

// Use the Windows display language (language packs are in distribution\extensions).
// https://firefox-admin-docs.mozilla.org/reference/policies/requestedlocales/
defaultPref("intl.locale.requested", "");
