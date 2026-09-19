from __future__ import annotations

import re
import time
from dataclasses import dataclass
from hashlib import sha256


@dataclass
class Tool: server:str; name:str; schema:str; risk:str; status:str="APPROVED"
@dataclass
class Delegation: human:str; agent:str; team:str; scopes:set[str]; expires:float
class Gateway:
 def __init__(self): self.tools={}; self.audit=[]; self.approvals={}; self.read_only=False
 def register(self,t:Tool): self.tools[(t.server,t.name)]=t
 def discover(self,d:Delegation):
  self._delegation(d); return [t.name for t in self.tools.values() if t.status=="APPROVED" and (t.risk=="READ" or "infra.write" in d.scopes)]
 def drift(self,server,name,new_schema):
  t=self.tools[(server,name)]
  if t.schema!=new_schema: t.status="QUARANTINED"; self.audit.append("TOOL_SCHEMA_CHANGED"); return True
  return False
 def call(self,d:Delegation,server,name,args,approval=None):
  self._delegation(d); t=self.tools.get((server,name))
  if not t or t.status!="APPROVED": return "DENY:untrusted tool"
  if self.read_only and t.risk!="READ": return "DENY:gateway read-only"
  if args.get("team") and args["team"]!=d.team:return "DENY:cross-team"
  if name=="scale_service" and (args.get("replicas",0)>10 or args.get("environment")=="production" and not approval): return "APPROVAL_REQUIRED"
  request_hash=sha256(repr((server,name,sorted(args.items()))).encode()).hexdigest()
  if approval and self.approvals.get(approval)!=request_hash:return "DENY:approval binding mismatch"
  response="API_KEY=demo-super-secret-value" if name=="get_synthetic_secret_demo" else f"executed:{name}"
  redacted=re.sub(r"API_KEY=[^\s]+","API_KEY=[REDACTED]",response)
  self.audit.append("RESPONSE_REDACTED" if redacted!=response else "TOOL_EXECUTED"); return redacted
 def approve(self,server,name,args):
  key=f"apr-{len(self.approvals)+1}"; self.approvals[key]=sha256(repr((server,name,sorted(args.items()))).encode()).hexdigest(); return key
 def _delegation(self,d):
  if d.expires<time.time():raise PermissionError("expired delegation")
