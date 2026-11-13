"""Simplified data model of the DORA Register of Information.

Based on Commission Implementing Regulation (EU) 2024/2956 (ITS on the register of information).
Only the six templates that matter most for data quality are modelled, with readable column names
(the ITS column codes are given in COLUMN_CODES). The real DPM uses coded values ("eba_..."): here the
human-readable labels of the ITS annexes are used instead.
"""

TEMPLATES = {
    "B_01.01": "Entity maintaining the register",
    "B_02.01": "Contractual arrangements - general information",
    "B_02.02": "Contractual arrangements - specific information",
    "B_05.01": "ICT third-party service providers",
    "B_06.01": "Functions",
    "B_07.01": "Assessment of the ICT services",
}

MANDATORY = {
    "B_01.01": ["fe_lei", "fe_name", "country", "entity_type", "competent_authority", "reporting_date"],
    "B_02.01": ["contract_ref", "arrangement_type", "currency", "annual_expense"],
    "B_02.02": ["contract_ref", "fe_lei", "provider_id", "provider_id_type", "function_id", "ict_service_type",
                "start_date", "end_date", "governing_law_country", "service_country", "data_storage",
                "data_sensitiveness", "reliance_level"],
    "B_05.01": ["provider_id", "provider_id_type", "provider_name", "person_type", "hq_country", "currency",
                "annual_expense"],
    "B_06.01": ["function_id", "function_name", "fe_lei", "criticality", "last_assessment_date", "rto_hours",
                "rpo_hours"],
    "B_07.01": ["contract_ref", "provider_id", "ict_service_type", "substitutability", "exit_plan",
                "reintegration_possible", "alternative_providers"],
}

KEYS = {
    "B_01.01": ["fe_lei"],
    "B_02.01": ["contract_ref"],
    "B_02.02": ["contract_ref", "fe_lei", "provider_id", "function_id", "ict_service_type"],
    "B_05.01": ["provider_id"],
    "B_06.01": ["function_id", "fe_lei"],
    "B_07.01": ["contract_ref", "provider_id", "ict_service_type"],
}

LEI_COLUMNS = {"B_01.01": ["fe_lei"], "B_02.02": ["fe_lei"], "B_06.01": ["fe_lei"],
               "B_05.01": ["provider_id", "ultimate_parent_id"]}

DATE_COLUMNS = {"B_01.01": ["reporting_date"], "B_02.02": ["start_date", "end_date"],
                "B_06.01": ["last_assessment_date"], "B_07.01": ["last_audit_date"]}

ICT_SERVICE_TYPES = {
    "S01": "ICT project management", "S02": "ICT development", "S03": "ICT help desk and first level support",
    "S04": "ICT security management services", "S05": "Provision of data", "S06": "Data analysis",
    "S07": "ICT, facilities and hosting services (excluding cloud)", "S08": "Computation",
    "S09": "Non-cloud data storage", "S10": "Telecom carrier", "S11": "Network infrastructure",
    "S12": "Hardware and physical devices", "S13": "Software licencing (excluding SaaS)",
    "S14": "ICT operation management", "S15": "ICT consulting", "S16": "ICT risk management",
    "S17": "Cloud services: IaaS", "S18": "Cloud services: PaaS", "S19": "Cloud services: SaaS",
}

import pycountry  # noqa: E402

COUNTRIES = {c.alpha_2 for c in pycountry.countries}          # ISO 3166-1 alpha-2
CURRENCIES = {c.alpha_3 for c in pycountry.currencies}        # ISO 4217

ALLOWED = {
    ("B_01.01", "country"): COUNTRIES,
    ("B_01.01", "entity_type"): {"Credit institution", "Investment firm", "UCITS management company",
                                 "Alternative investment fund manager", "Payment institution",
                                 "Electronic money institution", "Insurance undertaking"},
    ("B_02.01", "arrangement_type"): {"Standalone arrangement", "Overarching arrangement",
                                      "Subsequent or associated arrangement"},
    ("B_02.01", "currency"): CURRENCIES,
    ("B_02.02", "provider_id_type"): {"LEI", "EUID"},
    ("B_02.02", "ict_service_type"): set(ICT_SERVICE_TYPES),
    ("B_02.02", "governing_law_country"): COUNTRIES,
    ("B_02.02", "service_country"): COUNTRIES,
    ("B_02.02", "data_storage"): {"Yes", "No"},
    ("B_02.02", "data_sensitiveness"): {"Low", "Medium", "High"},
    ("B_02.02", "reliance_level"): {"Not significant", "Low reliance", "Material reliance", "Full reliance"},
    ("B_05.01", "provider_id_type"): {"LEI", "EUID"},
    ("B_05.01", "person_type"): {"Legal person", "Natural person"},
    ("B_05.01", "hq_country"): COUNTRIES,
    ("B_05.01", "currency"): CURRENCIES,
    ("B_06.01", "criticality"): {"Critical or important", "Not critical or important", "Assessment not performed"},
    ("B_07.01", "ict_service_type"): set(ICT_SERVICE_TYPES),
    ("B_07.01", "substitutability"): {"Not substitutable", "Highly complex substitutability",
                                      "Medium complexity in terms of substitutability", "Easily substitutable"},
    ("B_07.01", "exit_plan"): {"Yes", "No"},
    ("B_07.01", "reintegration_possible"): {"Easy", "Difficult", "Highly complex"},
    ("B_07.01", "alternative_providers"): {"Yes", "No"},
}

COLUMN_CODES = {  # readable name -> ITS column code (subset)
    ("B_01.01", "fe_lei"): "c0010", ("B_01.01", "fe_name"): "c0020", ("B_01.01", "country"): "c0030",
    ("B_02.01", "contract_ref"): "c0010", ("B_02.01", "arrangement_type"): "c0020",
    ("B_02.02", "contract_ref"): "c0010", ("B_02.02", "fe_lei"): "c0020", ("B_02.02", "provider_id"): "c0030",
    ("B_02.02", "function_id"): "c0050", ("B_02.02", "ict_service_type"): "c0060",
    ("B_02.02", "start_date"): "c0070", ("B_02.02", "end_date"): "c0080",
    ("B_05.01", "provider_id"): "c0010", ("B_05.01", "provider_name"): "c0050",
    ("B_06.01", "function_id"): "c0010", ("B_06.01", "criticality"): "c0050",
}
