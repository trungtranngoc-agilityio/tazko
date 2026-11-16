"""The audit log in control.db: who did what, when, from which address.

`service.record` takes the open write connection so the entry commits (or
rolls back) together with the change it describes. The Audit log admin page
arrives in M1-06.
"""
