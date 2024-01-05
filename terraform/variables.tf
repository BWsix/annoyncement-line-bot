variable "aws_region" {
  default     = "ap-northeast-1"
  description = "The AWS region to create things in. (Default: Tokyo)"
}

variable "credentials_path" {
  default     = "~/.aws/credentials"
  description = "AWS credentials path. Default = ~/.aws/credentials"
}

variable "project_name" {
  description = "Will be used to prefix aws resources."
  default     = "annoyncement-linebot"
}

variable "runtime" {
  default = "python3.11"
}

variable "linebot_access_token" {
  description = "Line bot access token"
}

variable "linebot_secret" {
  description = "Line bot secret"
}

variable "dashboard_url" {
  description = "Dashboard url"
}

