"""Super admin console API behind /admin.

Companies, company detail (members and invites) and invites across companies
are in router.py. TODO(M1-06): people, audit log, server page, Workspace domains.
Super admins see project names and counts, never boards. Every action is
audit-logged by the service it calls.
"""
