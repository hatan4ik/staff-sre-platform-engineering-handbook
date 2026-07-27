variable "generation" {
  description = "Logical configuration generation used to force a controlled replacement."
  type        = number
  default     = 1

  validation {
    condition     = var.generation >= 1 && floor(var.generation) == var.generation
    error_message = "generation must be a positive integer."
  }
}

variable "fail_after_create" {
  description = "Inject a local-exec failure after the managed file has been created."
  type        = bool
  default     = false
}
