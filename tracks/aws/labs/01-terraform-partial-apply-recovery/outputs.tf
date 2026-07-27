output "managed_file" {
  description = "Path to the locally managed object."
  value       = local_file.managed.filename
}

output "managed_content_sha256" {
  description = "Digest Terraform records for the managed file content."
  value       = local_file.managed.content_sha256
}

output "post_create_check_id" {
  description = "Identity of the post-create check resource."
  value       = terraform_data.post_create_check.id
}
