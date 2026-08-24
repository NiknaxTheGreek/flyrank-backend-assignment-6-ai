"""Versioned prompt contract for Assignment 6."""

PROMPT_VERSION = "support-classifier-v1"

SYSTEM_PROMPT = """You classify customer-support messages.
Return only JSON matching the required schema.
category must be one of: billing, bug, feature, other.
urgency must be one of: low, normal, high.
confidence must be a number from 0 to 1.
reason must be concise and grounded in the supplied message.
Do not add keys outside the schema.
""".strip()

REPAIR_PROMPT = """Your previous answer did not satisfy the required JSON schema.
Return one corrected JSON object only. Do not add prose, markdown, or extra keys.
""".strip()
