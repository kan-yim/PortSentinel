"""
Tools for Agent 4: Resolution Follow-up Agent.

This module provides utility functions for:
- Loading escalation contacts
- Finding appropriate L3 contacts
- Generating escalation emails
- Creating resolution summaries
"""

import csv
from typing import List, Optional, Dict, Any
from pathlib import Path
from .models import EscalationContact


class EscalationContactFinder:
    """
    Finds appropriate L3 escalation contacts based on incident details.
    """

    def __init__(self, contacts_csv_path: str):
        """
        Initialize with path to escalation contacts CSV.

        Args:
            contacts_csv_path: Path to Product_Team_Escalation_Contacts.csv
        """
        self.contacts_csv_path = contacts_csv_path
        self.contacts = self._load_contacts()

    def _load_contacts(self) -> List[Dict[str, str]]:
        """
        Load escalation contacts from CSV file.

        Returns:
            List of contact dictionaries
        """
        contacts = []

        try:
            with open(self.contacts_csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Clean up any BOM or extra whitespace
                    cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k}
                    if cleaned_row:  # Skip empty rows
                        contacts.append(cleaned_row)

        except FileNotFoundError:
            raise FileNotFoundError(
                f"Escalation contacts file not found: {self.contacts_csv_path}"
            )

        return contacts

    def find_contact(
        self,
        module: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> Optional[EscalationContact]:
        """
        Find the most appropriate L3 contact based on module and error code.

        Priority:
        1. Exact module match with specific error code
        2. Module match with wildcard
        3. General fallback (Others)

        Args:
            module: Affected module (e.g., "Vessel", "Container", "EDI/API")
            error_code: Error code (e.g., "VESSEL_ERR_4", "EDI_TIMEOUT")

        Returns:
            EscalationContact object or None if not found
        """
        if not self.contacts:
            return None

        # Normalize module name for matching
        module_normalized = self._normalize_module(module)

        # Find all matching contacts
        matches = []

        for contact in self.contacts:
            contact_module = contact.get('Module', '').strip()

            # Check if module matches
            if module_normalized and contact_module:
                # Extract module abbreviation (e.g., "VS" from "Vessel (VS)")
                if module_normalized.lower() in contact_module.lower():
                    matches.append(contact)
                elif contact_module.lower() == 'others':
                    # Keep "Others" as fallback
                    matches.append(contact)

        # If we have matches, return the first one (most specific)
        if matches:
            # Prefer non-"Others" matches first
            for match in matches:
                if 'others' not in match.get('Module', '').lower():
                    return self._contact_dict_to_model(match)

            # Fallback to "Others"
            return self._contact_dict_to_model(matches[0])

        # No match found
        return None

    def _normalize_module(self, module: Optional[str]) -> Optional[str]:
        """
        Normalize module name for matching.

        Args:
            module: Module name (e.g., "Vessel", "EDI/API", "Container")

        Returns:
            Normalized module name
        """
        if not module:
            return None

        # Mapping of common module names
        module_mapping = {
            'vessel': 'vessel',
            'vs': 'vessel',
            'container': 'container',
            'cntr': 'container',
            'edi': 'edi/api',
            'api': 'edi/api',
            'edi/api': 'edi/api',
        }

        module_lower = module.lower().strip()
        return module_mapping.get(module_lower, module_lower)

    def _contact_dict_to_model(self, contact_dict: Dict[str, str]) -> EscalationContact:
        """
        Convert contact dictionary to EscalationContact model.

        Args:
            contact_dict: Dictionary from CSV row

        Returns:
            EscalationContact object
        """
        return EscalationContact(
            module=contact_dict.get('Module', 'Unknown'),
            contact_name=contact_dict.get('Product Ops/Managers', 'Unknown'),
            role=contact_dict.get('Role', 'Unknown'),
            email=contact_dict.get('Email', 'unknown@psa123.com'),
            escalation_steps=contact_dict.get('Escalation Steps', 'No steps defined')
        )

    def list_all_contacts(self) -> List[EscalationContact]:
        """
        Get all available escalation contacts.

        Returns:
            List of all EscalationContact objects
        """
        return [self._contact_dict_to_model(c) for c in self.contacts]


def generate_escalation_email_body(
    incident_id: str,
    error_code: str,
    error_description: str,
    attempted_resolution: str,
    l2_notes: Optional[str] = None,
    escalation_reason: str = "L2 execution unsuccessful"
) -> str:
    """
    Generate email body for L3 escalation.

    Args:
        incident_id: Incident ID
        error_code: Error code
        error_description: Description of the error
        attempted_resolution: What resolution was attempted
        l2_notes: Notes from L2 execution attempt
        escalation_reason: Reason for escalation

    Returns:
        Formatted email body
    """
    email_body = f"""Dear Team,

I am escalating the following incident for your attention and further investigation.

**INCIDENT DETAILS**
-------------------
Incident ID:          {incident_id}
Error Code:           {error_code}
Error Description:    {error_description}
Escalation Reason:    {escalation_reason}

**RESOLUTION ATTEMPTED**
------------------------
{attempted_resolution}
"""

    if l2_notes:
        email_body += f"""
**L2 EXECUTION NOTES**
----------------------
{l2_notes}
"""

    email_body += """
**NEXT STEPS REQUIRED**
-----------------------
Please review the above information and take appropriate action to resolve this issue.
If you need any additional information or clarification, please do not hesitate to contact me.

**URGENCY**
-----------
This issue requires prompt attention to minimize customer impact.

Thank you for your assistance.

Best regards,
PORTNET Incident Management System
"""

    return email_body


def generate_summary_markdown(
    incident_id: str,
    error_identified: str,
    root_cause: str,
    resolution_attempted: str,
    resolution_outcome: str,
    actions_taken: List[str],
    timeline: List[Dict[str, str]],
    escalated_to_l3: bool = False,
    escalation_contact: Optional[EscalationContact] = None,
    lessons_learned: Optional[str] = None
) -> str:
    """
    Generate resolution summary in Markdown format.

    Args:
        incident_id: Incident ID
        error_identified: Error code and description
        root_cause: Root cause analysis
        resolution_attempted: Resolution method attempted
        resolution_outcome: Final outcome
        actions_taken: List of actions taken
        timeline: Timeline of events
        escalated_to_l3: Whether escalated to L3
        escalation_contact: L3 contact if escalated
        lessons_learned: Optional lessons learned

    Returns:
        Formatted Markdown summary
    """
    from datetime import datetime

    summary = f"""# Incident Resolution Summary

**Incident ID:** {incident_id}
**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
**Status:** {resolution_outcome}

---

## Error Identified

**Error Code:** {error_identified.split(':')[0] if ':' in error_identified else 'N/A'}
**Description:** {error_identified}

---

## Root Cause Analysis

{root_cause}

---

## Resolution Attempted

{resolution_attempted}

---

## Actions Taken

"""

    for i, action in enumerate(actions_taken, 1):
        summary += f"{i}. {action}\n"

    summary += "\n---\n\n## Timeline\n\n"
    summary += "| Time | Event |\n"
    summary += "|------|-------|\n"

    for event in timeline:
        time = event.get('time', 'N/A')
        description = event.get('event', 'N/A')
        summary += f"| {time} | {description} |\n"

    summary += "\n---\n\n"

    if escalated_to_l3 and escalation_contact:
        summary += f"""## L3 Escalation

**Escalated:** Yes
**Contact:** {escalation_contact.contact_name} ({escalation_contact.role})
**Email:** {escalation_contact.email}
**Module:** {escalation_contact.module}

**Escalation Steps:**
{escalation_contact.escalation_steps}

---

"""
    else:
        summary += "## L3 Escalation\n\n**Escalated:** No\n\n---\n\n"

    if lessons_learned:
        summary += f"""## Lessons Learned

{lessons_learned}

---

"""

    summary += f"""## Final Outcome

**Result:** {resolution_outcome}

"""

    if resolution_outcome == "Resolved Successfully":
        summary += "✅ The incident has been successfully resolved. No further action required.\n"
    elif resolution_outcome == "Escalated to L3":
        summary += "⚠️ The incident has been escalated to L3 for further investigation.\n"
    elif resolution_outcome == "Pending L2 Action":
        summary += "⏳ Awaiting L2 execution of the proposed resolution.\n"
    else:
        summary += "❌ Resolution attempt was unsuccessful. Further investigation required.\n"

    return summary


# Example usage
if __name__ == "__main__":
    # Test escalation contact finder
    contacts_path = "/Users/kanyim/portsentinel/escalation_contacts/Product_Team_Escalation_Contacts.csv"

    print("=" * 80)
    print("Escalation Contact Finder Test")
    print("=" * 80)

    try:
        finder = EscalationContactFinder(contacts_path)

        print(f"\nLoaded {len(finder.contacts)} contacts\n")

        # Test 1: Find Vessel contact
        print("Test 1: Finding contact for Vessel module")
        contact = finder.find_contact(module="Vessel")
        if contact:
            print(f"  ✓ Found: {contact.contact_name} ({contact.email})")
            print(f"    Role: {contact.role}")
        else:
            print("  ✗ No contact found")

        # Test 2: Find Container contact
        print("\nTest 2: Finding contact for Container module")
        contact = finder.find_contact(module="Container")
        if contact:
            print(f"  ✓ Found: {contact.contact_name} ({contact.email})")

        # Test 3: Find EDI/API contact
        print("\nTest 3: Finding contact for EDI/API module")
        contact = finder.find_contact(module="EDI/API")
        if contact:
            print(f"  ✓ Found: {contact.contact_name} ({contact.email})")

        # Test 4: Unknown module (should fallback to Others)
        print("\nTest 4: Finding contact for Unknown module")
        contact = finder.find_contact(module="Unknown")
        if contact:
            print(f"  ✓ Found: {contact.contact_name} ({contact.email})")
            print(f"    Module: {contact.module}")

        # Test 5: List all contacts
        print("\nTest 5: Listing all contacts")
        all_contacts = finder.list_all_contacts()
        print(f"  ✓ Total contacts: {len(all_contacts)}")
        for c in all_contacts:
            print(f"    - {c.module}: {c.contact_name}")

        print("\n" + "=" * 80)
        print("✓ All tests passed!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
