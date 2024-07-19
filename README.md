# Admin File Management Application

## Overview

The Admin File Management Application is designed to allow administrators to manage user access to files and folders within a specified system. It provides functionalities to view, create, and update user policies, including the ability to create new users and assign specific read/write permissions to them. The application uses FastAPI as the backend framework and Jinja2 for templating, with the file trees displayed using the `jstree` JavaScript plugin.

## Endpoints

### Admin Endpoints (`admin.py`)

The admin endpoints provide functionality for managing users and their access policies. These endpoints are protected and only accessible by users with administrative privileges.

- **User Management**
  - **Get User Information**: Retrieve information about a specific user or list all users.
  - **Add User**: Create a new user with a specified role and return the user's secret key.
  - **Remove User**: Delete an existing user from the system.

- **Policy Management**
  - **Get Policies**: Retrieve access policies for a specific user and resource.
  - **Add Policy**: Create a new policy granting a user access to a specified resource.
  - **Remove Policy**: Delete an existing policy for a user.

- **Asset Management**
  - **Get All Assets**: Retrieve and display all assets for a specific access point.
  - **File Management GUI**: Display an interface for managing files and folders, allowing administrators to assign user permissions.

### Asset Endpoints (`assets.py`)

The asset endpoints provide functionality for users to interact with their files and folders. These endpoints require user authentication and are designed to facilitate file uploads, downloads, and listing of user assets.

- **General and User Endpoints**
  - **List Assets**: Retrieve a list of all assets available to the authenticated user.
  - **Retrieve Asset**: Generate presigned URLs for accessing specific assets and serve an HTML template with these URLs.

- **Forms and User Interaction**
  - **Upload Form**: Render a form for uploading files, allowing users to select and upload files to the system.
  - **Download Form**: Render a form for downloading files, displaying available files and generating download links.

- **Presigned URL Endpoints**
  - **Generate Upload URL**: Create a presigned URL for uploading a file to the system.
  - **Generate Download URL**: Create presigned URLs for downloading assets, providing secure access to user files.

## Authentication and Authorization

- **Admin Access Control**: Admin endpoints use a decorator to ensure only users with administrative privileges can access them. The `is_admin` function validates the user's credentials and role.
- **User Validation**: The `validate_credentials` function checks user credentials for endpoints requiring user authentication, ensuring secure access to user-specific data.

## Utilities and Helper Functions

- **File Tree Conversion**: The `convert_file_tree_to_dict` function converts a file tree into a dictionary format suitable for rendering with the `jstree` plugin, facilitating the display of hierarchical file structures in the user interface.

## Templates

- **Jinja2 Templates**: The application uses Jinja2 templates to render HTML pages for various forms and interfaces, including user management, file upload, and download forms. These templates are dynamically populated with data from the backend to provide a seamless user experience.

## Summary

This application provides a robust system for managing user access to files and folders, with a strong focus on security and ease of use. Administrators can efficiently manage users and their permissions, while users can easily upload and download their files through an intuitive web interface.
