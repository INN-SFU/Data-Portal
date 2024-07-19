# Policy Derived Data Access Management Platform for Heterogenous Storage Endpoints

## Overview

This system is a prototype for a Data Access Management (DAM) serice/application to manage access to data assets on various storage enpoints (SE) via a centralized service. The primary goal is to create a one to one relation between a legal agreement defining the terms of use for a restricted data asset and the underlying technical implementation of that access with signed users of that policy. The implementation should be

1.  Agnostic about the nature of SEs
2.  Allow direct connection to SE for data transfer (as opposed to a connection via the DAM service host) where such connection is limited only to those assets granted by the signed policy
3.  Provide an easy to use and intuitive web based GUI for data asset administrators

This is a "glue code" application; the goal is not to develop a new standard or system, rather a generic tool and framework for connecting and managing policy restricted data assets. To this end three basic technical interfaces need to be defined

1.  Users - Data Access Manager
2.  Data Access Manager - Storage Enpoints
3.  Users - Storage Endpoints

These in effect form a trangular interaction whose connections are granted, but not conducted through, the DAM service.

```mermaid
graph TD;
    User<-->DAM;
    DAM<-->SE;
    User<-->SE;
```

Here the User - SE connection is token based where the token fully determines the parameters of the interaction (i.e. time expiry and scope). Tokens are granted via the User - DAM interface, derived from secrets shared between the DAM and SEs.


## User - Data Access Manager Interface

The User interacts with the DAM via web based API. Upon registration a user recieves a DAM access key. Administrators can then add user access to given assets according to their signed user policies. User policies are managed via an open source access control authorization library, (Casbin)[https://casbin.org/].  User policies in the casbin policy manager contain a reference to the storage end point, the file path string of the asset or assets (regular expressions can be used to cover sets of files according standard regular expression string matching), and the permission type: read or write. 

A user can see which assets they have access to and request a download or upload link to the asset/asset location. Requests are validated against the Casbin policy manager. If the request is valid, the DAM returns a token based access link to the relevant asset on the SE.

## Data Access Manager - Storage Enpoint Interface

The DAM is, in effect, a proxying authority for user access to SEs. Users themselves do not have credentials or access keys registered with the SE, however the DAM has credentials registered with the SEs. The reference structure to assets accross SE's needs to be standardized from the perspective of the DAM. To this end all SE are treated as hierarchical file systems, represented by a file tree, regardless of the SE's underlying file system. The generic class for this interface is defined by a (storage agent)[https://github.com/INN-SFU/Data-Portal/blob/main/core/connectivity/agent.py].

Each SE flavour (e.g. object store, posix based file server, etc..) will require a different, specific implementation of the agent class to interact with storage endpoint and return connections that mediate the User - Storage Endpoint interaction.

## User - Storage Endpoint Interface

The nature of this interface is ultimately determined by the storage endpoint in question. For object storage endpoints, presigned urls are generated for data assets by the DAM and returned to the user. This leverages the existing token based access infrastructure of object store endpoints. For other systems, e.g. posix systems, it's likely custom service applications will need to be running on the storage endpoints to implement similar functionality. This will require futher design and engineering decisions that have yet to be considered.

## Admin File Management Application

## Overview

The Admin File Management Application is designed to allow administrators to manage user access to files and folders within a specified system. It provides functionalities to view, create, and update user policies, including the ability to create new users and assign specific read/write permissions to them. The application uses FastAPI as the backend framework and Jinja2 for templating, with the file trees displayed using the `jstree` JavaScript plugin. The UI is rudimentary and are meant solely for the purpose of exposing endpoints and conecptualizing the fundamental workflows for the administrator.

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
