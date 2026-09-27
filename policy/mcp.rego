package mcp.authz

import rego.v1

default decision := {"allow": false, "approval_required": false, "reason": "default_deny"}

has_scope(scope) if {
  scope in input.identity.scopes
}

same_team if {
  not input.arguments.team
}

same_team if {
  input.arguments.team == input.identity.team
}

decision := {"allow": true, "approval_required": false, "reason": "read_allowed"} if {
  input.action == "discover"
  input.tool.name == "get_service_status"
  has_scope("infra.read")
}

decision := {"allow": true, "approval_required": false, "reason": "read_allowed"} if {
  input.action == "call"
  input.tool.name == "get_service_status"
  has_scope("infra.read")
  same_team
}

decision := {"allow": true, "approval_required": false, "reason": "utility_read_allowed"} if {
  input.action == "discover"
  input.tool.name == "get_synthetic_secret_demo"
  has_scope("infra.read")
}

decision := {"allow": true, "approval_required": false, "reason": "utility_read_allowed"} if {
  input.action == "call"
  input.tool.name == "get_synthetic_secret_demo"
  has_scope("infra.read")
}

decision := {"allow": true, "approval_required": false, "reason": "development_write_allowed"} if {
  input.action == "discover"
  input.tool.name == "scale_service"
  has_scope("infra.write")
}

decision := {"allow": true, "approval_required": false, "reason": "development_write_allowed"} if {
  input.action == "call"
  input.tool.name == "scale_service"
  has_scope("infra.write")
  same_team
  input.arguments.environment == "dev"
  input.arguments.replicas <= 10
}

decision := {"allow": false, "approval_required": true, "reason": "protected_write_requires_approval"} if {
  input.action == "call"
  input.tool.name == "scale_service"
  has_scope("infra.write")
  same_team
  input.arguments.environment == "production"
}
