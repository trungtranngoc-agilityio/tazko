"""Super admin console API behind /admin.

Companies, company detail (members and invites) and invites across companies
people, the audit log, the Server page and Workspace domains are in router.py;
service.py holds the pages that read across modules.
Super admins see project names and counts, never boards. Every action is
audit-logged by the service it calls.
"""
