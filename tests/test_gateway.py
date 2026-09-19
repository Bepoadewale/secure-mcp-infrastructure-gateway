import time

from mcpgw.core import Delegation, Gateway, Tool


def setup():
 g=Gateway(); g.register(Tool("infra","get_service_status","v1","READ")); g.register(Tool("infra","scale_service","v1","WRITE")); g.register(Tool("utility","get_synthetic_secret_demo","v1","READ")); return g
def d(scopes={"infra.write"}):return Delegation("alice","codex","payments",scopes,time.time()+60)
def test_discovery_and_parameter_denial():
 g=setup(); assert "scale_service" not in g.discover(d(set())); assert g.call(d(),"infra","scale_service",{"team":"identity","replicas":2})=="DENY:cross-team"
def test_exact_approval_binding():
 g=setup(); a={"team":"payments","environment":"production","replicas":6}; key=g.approve("infra","scale_service",a); assert g.call(d(),"infra","scale_service",a,key)=="executed:scale_service"; assert g.call(d(),"infra","scale_service",{**a,"replicas":20},key)=="APPROVAL_REQUIRED"
def test_schema_drift_and_redaction():
 g=setup(); assert g.drift("infra","scale_service","v2"); assert g.call(d(),"infra","scale_service",{"team":"payments","replicas":2})=="DENY:untrusted tool"; assert "secret" not in g.call(d(),"utility","get_synthetic_secret_demo",{})
def test_expired_delegation_and_kill_switch():
 g=setup();
 try:g.call(Delegation("a","b","payments",set(),0),"infra","get_service_status",{})
 except PermissionError:pass
 else:assert False
 g.read_only=True; assert g.call(d(),"infra","scale_service",{"team":"payments","replicas":2})=="DENY:gateway read-only"
