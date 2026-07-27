terraform {
  required_version = ">= 1.6.0"

  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

locals {
  runtime_directory = "${path.module}/runtime"
  managed_content   = "managed-generation-${var.generation}\n"
}

resource "terraform_data" "runtime_directory" {
  triggers_replace = [var.generation]

  provisioner "local-exec" {
    command = "mkdir -p '${local.runtime_directory}'"
  }
}

resource "local_file" "managed" {
  depends_on = [terraform_data.runtime_directory]

  filename        = "${local.runtime_directory}/managed.txt"
  content         = local.managed_content
  file_permission = "0644"
}

resource "terraform_data" "post_create_check" {
  depends_on = [local_file.managed]

  triggers_replace = [
    var.generation,
    local_file.managed.content_sha256,
  ]

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]

    command = var.fail_after_create ? <<-EOT
      echo 'Injected post-create failure after local_file.managed exists.' >&2
      echo 'The apply is intentionally incomplete; preserve evidence before recovery.' >&2
      exit 42
    EOT
    : <<-EOT
      printf 'check-passed generation=%s\n' '${var.generation}' \
        > '${local.runtime_directory}/check.txt'
    EOT
  }
}
