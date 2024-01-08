locals {
  bot_dir             = "${path.module}/../function"
  dynamodb_table_name = "${var.project_name}-groups"
}

provider "aws" {
  region                   = var.aws_region
  shared_credentials_files = [var.credentials_path]
}

// start of lambda

// lambda: role & policies
resource "aws_iam_role" "lambda" {
  assume_role_policy = data.aws_iam_policy_document.lambda.json
}
data "aws_iam_policy_document" "lambda" {
  statement {
    effect = "Allow"
    principals {
      identifiers = ["lambda.amazonaws.com"]
      type        = "Service"
    }
    actions = ["sts:AssumeRole"]
  }
}
resource "aws_iam_role_policy_attachment" "lambda_linebot" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
data "aws_iam_policy_document" "lambda_may_use_dynamo" {
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:*"]
    resources = [aws_dynamodb_table.groups.arn]
  }
}
resource "aws_iam_role_policy" "lambda_may_use_dynamo" {
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_may_use_dynamo.json
}
data "aws_iam_policy_document" "lambda_may_use_s3" {
  statement {
    effect  = "Allow"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.files.arn,
      "${aws_s3_bucket.files.arn}/*"
    ]
  }
}
resource "aws_iam_role_policy" "lambda_may_use_s3" {
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_may_use_s3.json
}

// lambda: source files & layer
data "archive_file" "lambda_source" {
  type        = "zip"
  output_path = "archives/lambda.zip"
  source_dir  = local.bot_dir
  excludes    = ["venv", "__pycache__"]
}
module "lambda_dependency_layer" {
  source              = "git::https://github.com/enter-at/terraform-aws-lambda-layer.git?ref=main"
  layer_name          = "${var.project_name}-dependencies"
  package_file        = "${local.bot_dir}/requirements.txt"
  compatible_runtimes = [var.runtime]
}

// lambda: linebot
resource "aws_lambda_function" "linebot" {
  function_name    = "${var.project_name}-linebot"
  filename         = data.archive_file.lambda_source.output_path
  source_code_hash = data.archive_file.lambda_source.output_base64sha256
  role             = aws_iam_role.lambda.arn
  handler          = "bot.lambda_handle_linebot"
  runtime          = var.runtime
  timeout          = 30
  layers           = ["${module.lambda_dependency_layer.arn}"]
  environment {
    variables = {
      LINEBOT_ACCESS_TOKEN = var.linebot_access_token
      LINEBOT_SECRET       = var.linebot_secret
      DASHBOARD_URL        = "${aws_amplify_app.dashboard.default_domain}/dashboard"
      DYNAMODB_TABLE_NAME  = local.dynamodb_table_name
      S3_BUCKET_NAME       = aws_s3_bucket.files.bucket
    }
  }
}
resource "aws_cloudwatch_log_group" "lambda_linebot" {
  name              = "/aws/lambda/${aws_lambda_function.linebot.function_name}"
  retention_in_days = 14
}
resource "aws_lambda_permission" "_" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.linebot.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api_gateway.execution_arn}/*"
}

// lambda: update line bot messaging api webhook url
resource "aws_lambda_function" "linebot_update_webhook_url" {
  function_name    = "${var.project_name}-linebot-update-webhook-url"
  filename         = data.archive_file.lambda_source.output_path
  source_code_hash = data.archive_file.lambda_source.output_base64sha256
  role             = aws_iam_role.lambda.arn
  handler          = "bot.lambda_update_webhook_url"
  runtime          = var.runtime
  timeout          = 30
  layers           = ["${module.lambda_dependency_layer.arn}"]
  environment {
    variables = {
      LINEBOT_ACCESS_TOKEN = var.linebot_access_token
      LINEBOT_SECRET       = var.linebot_secret
    }
  }
}
resource "aws_cloudwatch_log_group" "lambda_update_webhook_url" {
  name              = "/aws/lambda/${aws_lambda_function.linebot_update_webhook_url.function_name}"
  retention_in_days = 14
}
resource "aws_lambda_invocation" "update_webhook_url" {
  function_name = aws_lambda_function.linebot_update_webhook_url.function_name
  depends_on = [
    aws_api_gateway_deployment.prod
  ]
  input = jsonencode({
    url = "${aws_api_gateway_deployment.prod.invoke_url}/linebot"
  })
}

// lambda: activation
resource "aws_lambda_function" "activation" {
  function_name    = "${var.project_name}-activation"
  filename         = data.archive_file.lambda_source.output_path
  source_code_hash = data.archive_file.lambda_source.output_base64sha256
  role             = aws_iam_role.lambda.arn
  handler          = "activation.lambda_handle_activation"
  runtime          = var.runtime
  timeout          = 30
  layers           = ["${module.lambda_dependency_layer.arn}"]
  environment {
    variables = {
      LINEBOT_ACCESS_TOKEN = var.linebot_access_token
      LINEBOT_SECRET       = var.linebot_secret
      DYNAMODB_TABLE_NAME  = local.dynamodb_table_name
    }
  }
}
resource "aws_cloudwatch_log_group" "lambda_activation" {
  name              = "/aws/lambda/${aws_lambda_function.activation.function_name}"
  retention_in_days = 14
}
resource "aws_lambda_permission" "gateway_may_call_lambda_activation" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.activation.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api_gateway.execution_arn}/*"
}

// end of lambda

// start of api gateway
resource "aws_api_gateway_rest_api" "api_gateway" {
  name = var.project_name
}
resource "aws_api_gateway_deployment" "prod" {
  rest_api_id = aws_api_gateway_rest_api.api_gateway.id
  depends_on = [
    aws_api_gateway_integration.lambda_activate,
    aws_api_gateway_integration.lambda_linebot,
  ]
  triggers = {
    redeployment = sha1(jsonencode(aws_api_gateway_rest_api.api_gateway.body))
  }
  stage_name = "prod"
}

// gateway: linebot related
resource "aws_api_gateway_resource" "linebot" {
  rest_api_id = aws_api_gateway_rest_api.api_gateway.id
  parent_id   = aws_api_gateway_rest_api.api_gateway.root_resource_id
  path_part   = "linebot"
}
resource "aws_api_gateway_method" "linebot_any" {
  rest_api_id   = aws_api_gateway_rest_api.api_gateway.id
  resource_id   = aws_api_gateway_resource.linebot.id
  http_method   = "ANY"
  authorization = "NONE" // TODO: Only allow traffic coming from Line's server
}
resource "aws_api_gateway_integration" "lambda_linebot" {
  rest_api_id             = aws_api_gateway_rest_api.api_gateway.id
  resource_id             = aws_api_gateway_method.linebot_any.resource_id
  http_method             = aws_api_gateway_method.linebot_any.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.linebot.invoke_arn
}

// gateway: activation related
resource "aws_api_gateway_resource" "activate" {
  rest_api_id = aws_api_gateway_rest_api.api_gateway.id
  parent_id   = aws_api_gateway_rest_api.api_gateway.root_resource_id
  path_part   = "activate"
}
resource "aws_api_gateway_method" "activate_post" {
  rest_api_id   = aws_api_gateway_rest_api.api_gateway.id
  resource_id   = aws_api_gateway_resource.activate.id
  http_method   = "POST"
  authorization = "NONE"
}
resource "aws_api_gateway_integration" "lambda_activate" {
  rest_api_id             = aws_api_gateway_rest_api.api_gateway.id
  resource_id             = aws_api_gateway_method.activate_post.resource_id
  http_method             = aws_api_gateway_method.activate_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.activation.invoke_arn
}
module "cors_for_activation" {
  source          = "squidfunk/api-gateway-enable-cors/aws"
  version         = "0.3.3"
  api_id          = aws_api_gateway_rest_api.api_gateway.id
  api_resource_id = aws_api_gateway_resource.activate.id
}
// end of api gateway

// start of dynamo db
resource "aws_dynamodb_table" "groups" {
  name           = local.dynamodb_table_name
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "group_id"
  attribute {
    name = "group_id"
    type = "S"
  }
}
// end of dynamo db

// start of s3 bucket
resource "aws_s3_bucket" "files" {
  bucket_prefix = var.project_name
  force_destroy = true
}
resource "aws_s3_bucket_lifecycle_configuration" "files" {
  bucket = aws_s3_bucket.files.id
  rule {
    id     = "delete-old-files"
    status = "Enabled"
    expiration {
      days = 1
    }
  }
}
// end of s3 butcket

// start of amplify
resource "aws_iam_role" "amplify" {
  assume_role_policy = data.aws_iam_policy_document.amplify.json
}
data "aws_iam_policy_document" "amplify" {
  statement {
    effect = "Allow"
    principals {
      identifiers = ["amplify.amazonaws.com"]
      type        = "Service"
    }
    actions = ["sts:AssumeRole"]
  }
}
resource "aws_iam_role_policy_attachment" "amplify" {
  role       = aws_iam_role.amplify.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess-Amplify"
}
resource "aws_amplify_app" "dashboard" {
  name                 = "${var.project_name}-dashboard"
  repository           = var.repository
  build_spec           = file("amplify.yml")
  access_token         = var.github_access_token
  iam_service_role_arn = aws_iam_role.amplify.arn
}
resource "aws_amplify_branch" "dashboard_master" {
  app_id            = aws_amplify_app.dashboard.id
  branch_name       = "master"
  enable_auto_build = true
  framework         = "React"
  stage             = "PRODUCTION"
  environment_variables = {
    NEXT_PUBLIC_ACTIVATION_API = "${aws_api_gateway_deployment.prod.invoke_url}/activate"
  }
}
resource "aws_amplify_webhook" "dashboard" {
  app_id      = aws_amplify_app.dashboard.id
  branch_name = aws_amplify_branch.dashboard_master.branch_name
}
data "http" "trigger_build" {
  url    = aws_amplify_webhook.dashboard.url
  method = "POST"
}
// end of amplify
