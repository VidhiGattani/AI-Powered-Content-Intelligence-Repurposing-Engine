"""
Auth Stack - Cognito User Pool for Content Repurposing Platform
"""
from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_cognito as cognito,
)
from constructs import Construct


class AuthStack(Stack):
    """Creates Cognito User Pool for authentication"""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Cognito User Pool
        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name="content-repurposing-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False
            ),
            # Disable email verification for faster testing
            auto_verify=None,
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=False
                )
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=False,
                require_uppercase=False,
                require_digits=False,
                require_symbols=False
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.RETAIN
        )

        # User Pool Client
        self.user_pool_client = self.user_pool.add_client(
            "UserPoolClient",
            user_pool_client_name="content-repurposing-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            generate_secret=False
        )
