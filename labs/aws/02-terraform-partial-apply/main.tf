terraform {
  required_version = ">= 1.5.0"
}

variable "fail_database" {
  description = "Inject a failure after the network stage succeeds."
  type        = bool
  default     = true
}

locals {
  artifact_dir = "${path.module}/artifacts"
}

resource "terraform_data" "network" {
  input = {
    stage = "network"
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      set -eu
      mkdir -p "${local.artifact_dir}"
      printf 'stage=network status=created resource_id=%s\n' "$RESOURCE_ID" \
        > "${local.artifact_dir}/network.txt"
    EOT

    environment = {
      RESOURCE_ID = self.id
    }
  }
}

resource "terraform_data" "database" {
  input = {
    stage      = "database"
    network_id = terraform_data.network.id
  }

  # Changing the failure-injection switch deliberately replaces this toy
  # resource so its create-time provisioner executes again during recovery.
  triggers_replace = [var.fail_database]

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      set -eu
      mkdir -p "${local.artifact_dir}"
      printf 'stage=database status=attempted resource_id=%s network_id=%s\n' \
        "$RESOURCE_ID" "$NETWORK_ID" \
        > "${local.artifact_dir}/database-attempt.txt"

      if [ "$FAIL_DATABASE" = "true" ]; then
        printf 'injected database provisioning failure\n' >&2
        exit 42
      fi

      printf 'stage=database status=created resource_id=%s network_id=%s\n' \
        "$RESOURCE_ID" "$NETWORK_ID" \
        > "${local.artifact_dir}/database.txt"
    EOT

    environment = {
      FAIL_DATABASE = tostring(var.fail_database)
      NETWORK_ID     = terraform_data.network.id
      RESOURCE_ID    = self.id
    }
  }
}

resource "terraform_data" "application" {
  input = {
    stage       = "application"
    database_id = terraform_data.database.id
  }

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      set -eu
      mkdir -p "${local.artifact_dir}"
      printf 'stage=application status=created resource_id=%s database_id=%s\n' \
        "$RESOURCE_ID" "$DATABASE_ID" \
        > "${local.artifact_dir}/application.txt"
    EOT

    environment = {
      DATABASE_ID = terraform_data.database.id
      RESOURCE_ID = self.id
    }
  }
}

output "reconciliation_snapshot" {
  value = {
    fail_database = var.fail_database
    network_id    = terraform_data.network.id
    database_id   = try(terraform_data.database.id, null)
    application_id = try(terraform_data.application.id, null)
    artifact_dir  = local.artifact_dir
  }
}
