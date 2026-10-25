const Page = ({ title, children }) => (
  <div className="mx-auto max-w-3xl px-4 py-12">
    <h1 className="mb-1 text-2xl font-semibold">{title}</h1>
    <p className="mb-6 text-sm text-slate-500">Template text for a campus deployment. Have your institution's legal team review it before launch.</p>
    <div className="space-y-4 text-sm leading-relaxed text-slate-700">{children}</div>
  </div>
);

export const Privacy = () => (
  <Page title="Privacy policy">
    <p><b>What we store.</b> Your name, college email, optional department/year/student identifier, the reports, comments, messages and claims you create, and an audit log of sensitive actions.</p>
    <p><b>What others can see.</b> Other users see your first name and last initial. Your email, student identifier, private identifying details and claim evidence are never shown publicly. They are visible only to authorised reviewers when needed to verify a claim.</p>
    <p><b>Private messages</b> are visible to the two participants. Administrators may open a conversation for moderation and each such access is logged.</p>
    <p><b>Retention.</b> Reports may be expired automatically after the period configured by administrators. Ask campus support to remove your account data.</p>
  </Page>
);

export const Terms = () => (
  <Page title="Terms of use">
    <p>Use RecoverIQ only to report and recover genuine lost property. Do not post false reports, abusive content, or other people's private information.</p>
    <p>A similarity estimate is only a suggestion and never proves ownership. Items held by campus staff are released only after an authorised staff member approves a claim and records a handover.</p>
    <p>Accounts that misuse the platform may be deactivated by administrators. Suspicious content can be reported with the "Report abuse" action.</p>
  </Page>
);
