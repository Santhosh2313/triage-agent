import os
import json
import re
from anthropic import Anthropic
from dotenv import load_dotenv
from retriever import Retriever

load_dotenv()

class SupportAgent:
    def __init__(self, fast_mode=False):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.retriever = Retriever(fast_mode=fast_mode)
        self.model = "claude-3-5-sonnet-20241022" # Using standard Sonnet 3.5

    def classify_company(self, issue, subject, company):
        if company and str(company).lower() not in ["none", "nan"]:
            return str(company)
        
        # Simple inference or let LLM decide? 
        # Instructions say "infer from content". We'll do a quick check then fallback to LLM in system prompt if needed.
        issue_lower = (issue + " " + (subject or "")).lower()
        if "hackerrank" in issue_lower: return "HackerRank"
        if "claude" in issue_lower: return "Claude"
        if "visa" in issue_lower: return "Visa"
        return "Unknown"

    def should_escalate(self, issue, subject, company, docs):
        text = (issue + " " + (subject or "")).lower()
        
        # Keyword-based escalation
        escalation_keywords = [
            "fraud", "unauthorized", "stolen", "compromised", "hacked", "chargeback", "dispute",
            "locked out", "can't login", "account suspended", "banned",
            "legal", "gdpr", "data deletion", "privacy request", "subpoena",
            "cheating", "plagiarism", "integrity violation",
            "threat", "abuse", "harassment",
            "my money", "lost funds", "transfer without permission"
        ]
        
        for kw in escalation_keywords:
            if kw in text:
                return True, f"Escalated due to sensitive keyword: {kw}"

        # No relevant docs
        if not docs:
            return True, "Escalated because no relevant support documentation was found."

        # Ambiguous security/billing
        if any(x in text for x in ["billing", "payment", "card", "security", "access"]) and len(docs) < 1:
            return True, "Ambiguous security/billing issue with low confidence in docs."

        # Company None and security/financial
        if company == "Unknown" and any(x in text for x in ["money", "hacked", "stolen", "account"]):
             return True, "Unidentified company with security/financial concerns."

        return False, ""

    def process_ticket(self, issue, subject, company_input):
        company = self.classify_company(issue, subject, company_input)
        
        # Retrieve docs
        source_filter = company.lower() if company != "Unknown" else None
        docs = self.retriever.search(f"{subject} {issue}", source_filter=source_filter, top_k=5)
        
        # Immediate risk assessment
        escalate_now, reason = self.should_escalate(issue, subject, company, docs)
        
        # Even if we escalate, we can ask Claude for the response formatting
        # but if we have a hard escalation, we'll force it.
        
        docs_text = ""
        for i, doc in enumerate(docs):
            docs_text += f"[Doc {i+1} - {doc['title']}]\n{doc['content']}\n\n"

        system_prompt = f"""You are a support triage agent for {company}. You must ONLY use the provided support documentation to answer. Never hallucinate policies or features.

For each ticket, return a JSON object with:
{{
  "status": "replied" | "escalated",
  "product_area": "<category>",
  "request_type": "product_issue" | "feature_request" | "bug" | "invalid",
  "response": "<user-facing response>",
  "justification": "<internal reasoning>"
}}

Rules:
- If the issue is answerable from docs → status: replied
- If the issue is risky, sensitive, or undocumented → status: escalated
- If irrelevant or malicious → request_type: invalid, status: replied with out-of-scope message
- If escalated, response must say "We're escalating your case to a human agent" + brief reason
- Keep response professional, concise, and grounded in provided docs
- Never make up policies
"""

        user_message = f"""COMPANY: {company}
SUBJECT: {subject}
ISSUE: {issue}

RELEVANT SUPPORT DOCS:
{docs_text}
"""

        if escalate_now:
            # We can still use Claude to categorize it, but we'll force status: escalated
            system_prompt += f"\nIMPORTANT: This ticket has been pre-flagged for escalation. You MUST set 'status' to 'escalated' and provided a reason in 'response'."

        response_json = self._call_claude(system_prompt, user_message)
        
        if not response_json:
            # Fallback for crash
            return {
                "company": company,
                "status": "escalated",
                "product_area": "Unknown",
                "request_type": "product_issue",
                "response": "We're escalating your case to a human agent due to a processing error.",
                "justification": "LLM processing failed.",
                "docs": docs
            }

        response_json["company"] = company
        response_json["docs"] = docs
        return response_json

    def _call_claude(self, system, user, retry=True):
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}]
            )
            content = message.content[0].text
            return self._parse_json(content)
        except Exception as e:
            if retry:
                print(f"JSON parsing or API error: {e}. Retrying with stricter prompt...")
                stricter_system = system + "\nReturn ONLY valid JSON. No other text."
                return self._call_claude(stricter_system, user, retry=False)
            print(f"Final error calling Claude: {e}")
            return None

    def _parse_json(self, text):
        # Clean up text if LLM added preamble
        try:
            # Find the first { and last }
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return json.loads(text)
        except:
            return None
