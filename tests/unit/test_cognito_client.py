import pytest

from src.credentials.cognito_client import CognitoAuthError, initiate_password_auth


def test_initiate_password_auth_requires_client_id():
    with pytest.raises(CognitoAuthError, match="SYBOL_COGNITO_CLIENT_ID"):
        initiate_password_auth("user@ie.id", "secret", client_id="")


def test_initiate_password_auth_maps_tokens(mocker):
    mock_response = mocker.Mock()
    mock_response.is_success = True
    mock_response.json.return_value = {
        "AuthenticationResult": {
            "AccessToken": "access-abc",
            "IdToken": "id-xyz",
            "RefreshToken": "refresh-123",
        }
    }
    mocker.patch(
        "src.credentials.cognito_client.httpx.post", return_value=mock_response
    )

    tokens = initiate_password_auth(
        "user@ie.id",
        "secret",
        client_id="client-id",
        region="eu-west-1",
    )

    assert tokens == {
        "accessToken": "access-abc",
        "idToken": "id-xyz",
        "refreshToken": "refresh-123",
    }


def test_initiate_password_auth_challenge(mocker):
    mock_response = mocker.Mock()
    mock_response.is_success = True
    mock_response.json.return_value = {"ChallengeName": "SOFTWARE_TOKEN_MFA"}
    mocker.patch(
        "src.credentials.cognito_client.httpx.post", return_value=mock_response
    )

    with pytest.raises(CognitoAuthError, match="SOFTWARE_TOKEN_MFA"):
        initiate_password_auth(
            "user@ie.id",
            "secret",
            client_id="client-id",
        )


def test_initiate_password_auth_not_authorized(mocker):
    mock_response = mocker.Mock()
    mock_response.is_success = False
    mock_response.text = "Not authorized"
    mock_response.json.return_value = {
        "__type": "NotAuthorizedException",
        "message": "Incorrect username or password.",
    }
    mocker.patch(
        "src.credentials.cognito_client.httpx.post", return_value=mock_response
    )

    with pytest.raises(CognitoAuthError, match="Incorrect username or password"):
        initiate_password_auth(
            "user@ie.id",
            "wrong",
            client_id="client-id",
        )
