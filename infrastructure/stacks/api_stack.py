"""API Gateway stack for Content Repurposing Platform."""

from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
    aws_iam as iam,
    Duration,
)
from constructs import Construct


class ApiStack(Stack):
    """Stack for API Gateway and Lambda handlers."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        user_pool_id: str,
        user_pool_client_id: str,
        original_content_bucket: str,
        generated_content_bucket: str,
        style_vault_bucket: str,
        transcripts_bucket: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Store bucket names for Lambda environment variables
        self.original_content_bucket = original_content_bucket
        self.generated_content_bucket = generated_content_bucket
        self.style_vault_bucket = style_vault_bucket
        self.transcripts_bucket = transcripts_bucket

        # Create API Gateway with CORS for browser-to-API (e.g. CloudFront -> API Gateway)
        self.api = apigw.RestApi(
            self,
            "ContentRepurposingApi",
            rest_api_name="Content Repurposing Platform API",
            description="API for AI-powered content repurposing platform",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                ],
            ),
        )

        # Add CORS headers to API Gateway error responses (4xx/5xx) so browser doesn't block
        self.api.add_gateway_response(
            "Default4xxCors",
            type=apigw.ResponseType.DEFAULT_4_XX,
            response_headers={
                "Access-Control-Allow-Origin": "'*'",
                "Access-Control-Allow-Headers": "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'",
            },
        )
        self.api.add_gateway_response(
            "Default5xxCors",
            type=apigw.ResponseType.DEFAULT_5_XX,
            response_headers={
                "Access-Control-Allow-Origin": "'*'",
                "Access-Control-Allow-Headers": "'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token'",
            },
        )

        # Create Lambda execution role with necessary permissions
        lambda_role = iam.Role(
            self,
            "ApiLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Add permissions for AWS services
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:*",
                    "dynamodb:*",
                    "s3:*",
                    "bedrock:*",
                    "transcribe:*",
                ],
                resources=["*"],
            )
        )

        # Create Lambda layer for shared dependencies
        lambda_layer = lambda_.LayerVersion(
            self,
            "SharedDependencies",
            code=lambda_.Code.from_asset("lambda_layer"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="Shared dependencies for Lambda functions",
        )

        # Authentication endpoints
        auth_resource = self.api.root.add_resource("auth")
        self._create_auth_endpoints(auth_resource, lambda_role, lambda_layer, user_pool_id, user_pool_client_id)

        # Style profile endpoints
        style_resource = self.api.root.add_resource("style-content")
        self._create_style_endpoints(style_resource, lambda_role, lambda_layer)

        # Content endpoints
        content_resource = self.api.root.add_resource("content")
        self._create_content_endpoints(content_resource, lambda_role, lambda_layer, user_pool_id, user_pool_client_id)

        # Generation endpoints
        generate_resource = self.api.root.add_resource("generate")
        self._create_generation_endpoints(generate_resource, lambda_role, lambda_layer, user_pool_id, user_pool_client_id)

        # SEO endpoints
        seo_resource = self.api.root.add_resource("seo")
        self._create_seo_endpoints(seo_resource, lambda_role, lambda_layer)

        # Scheduling endpoints
        schedule_resource = self.api.root.add_resource("schedule")
        self._create_scheduling_endpoints(schedule_resource, lambda_role, lambda_layer)

    def _create_lambda(
        self,
        function_id: str,
        handler: str,
        role: iam.Role,
        layer: lambda_.LayerVersion,
        environment: dict = None,
    ) -> lambda_.Function:
        """Create a Lambda function with common configuration."""
        return lambda_.Function(
            self,
            function_id,
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler=handler,
            code=lambda_.Code.from_asset("lambda_handlers"),
            role=role,
            layers=[layer],
            timeout=Duration.seconds(30),
            environment=environment or {},
        )

    def _create_auth_endpoints(
        self,
        resource: apigw.Resource,
        role: iam.Role,
        layer: lambda_.LayerVersion,
        user_pool_id: str,
        user_pool_client_id: str,
    ) -> None:
        """Create authentication endpoints."""
        env = {
            "COGNITO_USER_POOL_ID": user_pool_id,
            "COGNITO_USER_POOL_CLIENT_ID": user_pool_client_id,
            "USER_POOL_ID": user_pool_id,
            "USER_POOL_CLIENT_ID": user_pool_client_id,
        }

        # POST /auth/signup
        signup_lambda = self._create_lambda(
            "SignupFunction", "auth.signup_handler", role, layer, env
        )
        signup_resource = resource.add_resource("signup")
        signup_resource.add_method(
            "POST",
            apigw.LambdaIntegration(signup_lambda, proxy=True),
        )

        # POST /auth/signin
        signin_lambda = self._create_lambda(
            "SigninFunction", "auth.signin_handler", role, layer, env
        )
        signin_resource = resource.add_resource("signin")
        signin_resource.add_method(
            "POST",
            apigw.LambdaIntegration(signin_lambda, proxy=True),
        )

        # POST /auth/signout
        signout_lambda = self._create_lambda(
            "SignoutFunction", "auth.signout_handler", role, layer, env
        )
        signout_resource = resource.add_resource("signout")
        signout_resource.add_method("POST", apigw.LambdaIntegration(signout_lambda, proxy=True))

        # POST /auth/refresh
        refresh_lambda = self._create_lambda(
            "RefreshFunction", "auth.refresh_handler", role, layer, env
        )
        refresh_resource = resource.add_resource("refresh")
        refresh_resource.add_method("POST", apigw.LambdaIntegration(refresh_lambda, proxy=True))

    def _create_style_endpoints(
        self, resource: apigw.Resource, role: iam.Role, layer: lambda_.LayerVersion
    ) -> None:
        """Create style profile endpoints."""
        # POST /style-content (upload)
        upload_lambda = self._create_lambda(
            "StyleUploadFunction", "style.upload_handler", role, layer
        )
        resource.add_method("POST", apigw.LambdaIntegration(upload_lambda, proxy=True))

        # GET /style-profile
        profile_resource = self.api.root.add_resource("style-profile")
        get_profile_lambda = self._create_lambda(
            "GetStyleProfileFunction", "style.get_profile_handler", role, layer
        )
        profile_resource.add_method("GET", apigw.LambdaIntegration(get_profile_lambda, proxy=True))

        # DELETE /style-content/:id
        delete_resource = resource.add_resource("{id}")
        delete_lambda = self._create_lambda(
            "DeleteStyleContentFunction", "style.delete_handler", role, layer
        )
        delete_resource.add_method("DELETE", apigw.LambdaIntegration(delete_lambda, proxy=True))

    def _create_content_endpoints(
        self, resource: apigw.Resource, role: iam.Role, layer: lambda_.LayerVersion,
        user_pool_id: str, user_pool_client_id: str
    ) -> None:
        """Create content endpoints."""
        env = {
            "COGNITO_USER_POOL_ID": user_pool_id,
            "COGNITO_USER_POOL_CLIENT_ID": user_pool_client_id,
            "USER_POOL_ID": user_pool_id,
            "USER_POOL_CLIENT_ID": user_pool_client_id,
            "S3_BUCKET_ORIGINAL_CONTENT": self.original_content_bucket,
            "S3_BUCKET_GENERATED_CONTENT": self.generated_content_bucket,
            "S3_BUCKET_STYLE_VAULT": self.style_vault_bucket,
            "S3_BUCKET_TRANSCRIPTS": self.transcripts_bucket,
            "DYNAMODB_TABLE_ORIGINAL_CONTENT": "original_content",
            "DYNAMODB_TABLE_GENERATED_CONTENT": "generated_content",
            "DYNAMODB_TABLE_STYLE_VAULT": "style_vault",
            "DYNAMODB_TABLE_USERS": "users",
        }
        # POST /content (upload)
        upload_lambda = self._create_lambda(
            "ContentUploadFunction", "content.upload_handler", role, layer, env
        )
        resource.add_method("POST", apigw.LambdaIntegration(upload_lambda, proxy=True))

        # GET /content (list)
        list_lambda = self._create_lambda(
            "ContentListFunction", "content.list_handler", role, layer, env
        )
        resource.add_method("GET", apigw.LambdaIntegration(list_lambda, proxy=True))

        # GET /content/:id
        id_resource = resource.add_resource("{id}")
        get_lambda = self._create_lambda(
            "GetContentFunction", "content.get_handler", role, layer, env
        )
        id_resource.add_method("GET", apigw.LambdaIntegration(get_lambda, proxy=True))

        # DELETE /content/:id
        delete_lambda = self._create_lambda(
            "DeleteContentFunction", "content.delete_handler", role, layer, env
        )
        id_resource.add_method("DELETE", apigw.LambdaIntegration(delete_lambda, proxy=True))

    def _create_generation_endpoints(
        self, resource: apigw.Resource, role: iam.Role, layer: lambda_.LayerVersion,
        user_pool_id: str, user_pool_client_id: str
    ) -> None:
        """Create generation endpoints."""
        env = {
            "COGNITO_USER_POOL_ID": user_pool_id,
            "COGNITO_USER_POOL_CLIENT_ID": user_pool_client_id,
            "USER_POOL_ID": user_pool_id,
            "USER_POOL_CLIENT_ID": user_pool_client_id,
            "S3_BUCKET_ORIGINAL_CONTENT": self.original_content_bucket,
            "S3_BUCKET_GENERATED_CONTENT": self.generated_content_bucket,
            "S3_BUCKET_STYLE_VAULT": self.style_vault_bucket,
            "S3_BUCKET_TRANSCRIPTS": self.transcripts_bucket,
            "DYNAMODB_TABLE_ORIGINAL_CONTENT": "original_content",
            "DYNAMODB_TABLE_GENERATED_CONTENT": "generated_content",
            "DYNAMODB_TABLE_STYLE_VAULT": "style_vault",
            "DYNAMODB_TABLE_USERS": "users",
        }
        
        # POST /generate (initial generation)
        generate_lambda = self._create_lambda(
            "GenerateFunction", "generation.generate_handler", role, layer, env
        )
        resource.add_method("POST", apigw.LambdaIntegration(generate_lambda, proxy=True))

        # POST /regenerate/:id
        regenerate_resource = self.api.root.add_resource("regenerate")
        id_resource = regenerate_resource.add_resource("{id}")
        regenerate_lambda = self._create_lambda(
            "RegenerateFunction", "generation.regenerate_handler", role, layer, env
        )
        id_resource.add_method("POST", apigw.LambdaIntegration(regenerate_lambda, proxy=True))

        # GET /generated/:id
        generated_resource = self.api.root.add_resource("generated")
        get_resource = generated_resource.add_resource("{id}")
        get_lambda = self._create_lambda(
            "GetGeneratedFunction", "generation.get_handler", role, layer, env
        )
        get_resource.add_method("GET", apigw.LambdaIntegration(get_lambda, proxy=True))

        # PUT /generated/:id/edit
        edit_resource = get_resource.add_resource("edit")
        edit_lambda = self._create_lambda(
            "EditGeneratedFunction", "generation.edit_handler", role, layer, env
        )
        edit_resource.add_method("PUT", apigw.LambdaIntegration(edit_lambda, proxy=True))

        # POST /generated/:id/approve
        approve_resource = get_resource.add_resource("approve")
        approve_lambda = self._create_lambda(
            "ApproveGeneratedFunction", "generation.approve_handler", role, layer, env
        )
        approve_resource.add_method("POST", apigw.LambdaIntegration(approve_lambda, proxy=True))

    def _create_seo_endpoints(
        self, resource: apigw.Resource, role: iam.Role, layer: lambda_.LayerVersion
    ) -> None:
        """Create SEO endpoints."""
        # POST /seo/titles
        titles_resource = resource.add_resource("titles")
        titles_lambda = self._create_lambda(
            "GenerateTitlesFunction", "seo.titles_handler", role, layer
        )
        titles_resource.add_method("POST", apigw.LambdaIntegration(titles_lambda, proxy=True))

        # POST /seo/hashtags
        hashtags_resource = resource.add_resource("hashtags")
        hashtags_lambda = self._create_lambda(
            "GenerateHashtagsFunction", "seo.hashtags_handler", role, layer
        )
        hashtags_resource.add_method("POST", apigw.LambdaIntegration(hashtags_lambda, proxy=True))

        # POST /seo/alt-text
        alttext_resource = resource.add_resource("alt-text")
        alttext_lambda = self._create_lambda(
            "GenerateAltTextFunction", "seo.alttext_handler", role, layer
        )
        alttext_resource.add_method("POST", apigw.LambdaIntegration(alttext_lambda, proxy=True))

    def _create_scheduling_endpoints(
        self, resource: apigw.Resource, role: iam.Role, layer: lambda_.LayerVersion
    ) -> None:
        """Create scheduling endpoints."""
        # POST /schedule
        create_lambda = self._create_lambda(
            "CreateScheduleFunction", "scheduling.create_handler", role, layer
        )
        resource.add_method("POST", apigw.LambdaIntegration(create_lambda, proxy=True))

        # GET /schedule (list)
        list_lambda = self._create_lambda(
            "ListSchedulesFunction", "scheduling.list_handler", role, layer
        )
        resource.add_method("GET", apigw.LambdaIntegration(list_lambda, proxy=True))

        # DELETE /schedule/:id
        id_resource = resource.add_resource("{id}")
        delete_lambda = self._create_lambda(
            "DeleteScheduleFunction", "scheduling.delete_handler", role, layer
        )
        id_resource.add_method("DELETE", apigw.LambdaIntegration(delete_lambda, proxy=True))

        # GET /schedule/optimal-times
        optimal_resource = resource.add_resource("optimal-times")
        optimal_lambda = self._create_lambda(
            "OptimalTimesFunction", "scheduling.optimal_times_handler", role, layer
        )
        optimal_resource.add_method("GET", apigw.LambdaIntegration(optimal_lambda, proxy=True))
