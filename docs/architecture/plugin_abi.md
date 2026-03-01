# Plugin ABI

## Overview
This document defines the Application Binary Interface (ABI) for plugins in our system. The ABI ensures that plugins can be loaded and executed by the host application without compatibility issues.

## Contract Details
### Identity
- `plugin_id`: Unique identifier for the plugin.
- `name`: Human-readable name of the plugin.
- `version`: Version number of the plugin.
- `api_version`: Version of the API that the plugin is compatible with.
- `plugin_type`: Type of the plugin (e.g., Input, Output, Capture).

### Lifecycle Methods
- `Initialize(Services*)`: Initializes the plugin with necessary services.
- `Start(Profile*)`: Starts the plugin with a given profile.
- `Stop()`: Stops the plugin.
- `Shutdown()`: Shuts down the plugin and releases resources.

### Capabilities
- `GetCapabilities()`: Returns the capabilities of the plugin in a structured, versioned format.

### Policy
- `required_entitlements[]`: List of entitlements required by the plugin.
- `requires_drivers[]`: List of drivers required by the plugin.
- `requires_worker(bool)`: Indicates if the plugin requires a worker process.

## Trust and Signing
- All plugins must be publisher-signed.
- The host verifies the signature and ABI/api compatibility before loading any plugin.
- Premium plugins must not be loadable until the user completes a purchase and entitlement checks succeed.

## On-demand Loading
- Users can load additional plugin DLLs at runtime if they are signed and policy-allowed.
- If a selected DLL is Premium and the user is not entitled, the host blocks loading and routes the user to the purchase flow.