Feature: Configuration Loading
  As a system administrator
  I want to ensure configuration is loaded correctly
  So that the application starts with proper settings

  Scenario: Load configuration with default values
    Given I have a valid configuration file
    When I load the configuration with EnvYAML
    Then the configuration should be loaded successfully
    And the port should be an integer
    And the reload setting should be a boolean
    And the reset setting should be a boolean

  Scenario: Environment variable override
    Given I have a valid configuration file
    And I set environment variable "AMS_PORT" to "9000"
    When I load the configuration with EnvYAML
    Then the port should be 9000
    And the port should be an integer