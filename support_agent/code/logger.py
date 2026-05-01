import os

class Logger:
    def __init__(self, log_path=None):
        if log_path is None:
            log_path = os.path.join(os.path.dirname(__file__), "..", "data", "logs", "log.txt")
        self.log_path = os.path.abspath(log_path)
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log_ticket(self, ticket_num, input_data, agent_output):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"=== TICKET #{ticket_num} ===\n")
            f.write(f"Company: {agent_output.get('company', 'Unknown')}\n")
            f.write(f"Subject: {input_data.get('subject', '')}\n")
            f.write(f"Issue: {input_data.get('issue', '')}\n\n")
            
            f.write("Retrieved Docs:\n")
            docs = agent_output.get('docs', [])
            for i, doc in enumerate(docs):
                f.write(f"  {i+1}. [{doc['source']}] {doc['title']} - {doc['url']}\n")
            
            f.write("\nAgent Decision:\n")
            f.write(f"  Status: {agent_output.get('status', 'N/A')}\n")
            f.write(f"  Request Type: {agent_output.get('request_type', 'N/A')}\n")
            f.write(f"  Product Area: {agent_output.get('product_area', 'N/A')}\n")
            f.write(f"  Response: {agent_output.get('response', 'N/A')}\n")
            f.write(f"  Justification: {agent_output.get('justification', 'N/A')}\n")
            f.write("\n" + "="*30 + "\n\n")
