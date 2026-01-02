%% Poelis MATLAB Toolbox - Example Usage
% This script demonstrates how to use the Poelis MATLAB Toolbox
% which provides a native MATLAB interface with automatic type conversions.
%
% Prerequisites:
%   1. Install poelis-sdk Python package in a virtual environment: pip install poelis-sdk
%   2. Configure MATLAB Python environment: pyenv('Version', '/path/to/venv/bin/python')

%% Setup: Initialize the Poelis Client

% Initialize the client with your API key

% TODO: If not already set, replace with your actual venv path
% pyenv('Version', '/path/to/venv/bin/python');

% TODO: Replace with your actual API key
api_key = 'your-api-key';

poelis = poelis_sdk.PoelisClient(api_key);
fprintf('✓ Poelis client initialized\n\n');

%% Example 1: List Available Workspaces

fprintf('=== Example 1: Listing Workspaces ===\n');
workspaces = poelis.list_children(); 
fprintf('Available workspaces (%d):\n', length(workspaces));
for i = 1:length(workspaces)
    fprintf('  - %s\n', workspaces(i));
end
fprintf('\n');

%% Example 2: Get a Single Property Value

fprintf('=== Example 2: Getting a Property Value ===\n');

% TODO: Replace with your actual path
path = 'demo_workspace.demo_product.demo_item.demo_sub_item.demo_property_mass';

value = poelis.get_value(path);
fprintf('Property path: %s\n', path);
fprintf('Value: %.2f\n', value);
fprintf('Type: %s\n', class(value));
fprintf('\n');

%% Example 3: Get Property Information (Value, Unit, Category)

fprintf('=== Example 3: Getting Property Information ===\n');
info = poelis.get_property('demo_workspace.demo_product.demo_item.demo_sub_item.demo_property_mass');

fprintf('Property Name: %s\n', info.name);
fprintf('Value: %.2f %s\n', info.value, info.unit);
fprintf('Category: %s\n', info.category);
fprintf('\n');

%% Example 4: Explore Available Nodes

fprintf('=== Example 4: Exploring Available Nodes ===\n');

% TODO: Replace with your actual workspace, product, and item names
workspace_name = 'demo_workspace';
product_name = 'demo_product';
item_name = 'demo_item';

% List products in workspace
fprintf('Listing products in workspace: %s\n', workspace_name);
products = poelis.list_children(workspace_name);
fprintf('Products (%d): %s\n', length(products), strjoin(products, ', '));
fprintf('\n');

% List items in product (path automatically resolves through baseline)
fprintf('Listing items in product: %s.%s\n', workspace_name, product_name);
item_path = [workspace_name, '.', product_name];
items = poelis.list_children(item_path);
fprintf('Items (%d): %s\n', length(items), strjoin(items, ', '));
fprintf('\n');

% List properties of a specific item
fprintf('Listing properties of item: %s.%s.%s\n', workspace_name, product_name, item_name);
full_item_path = [workspace_name, '.', product_name, '.', item_name];
properties = poelis.list_properties(full_item_path);
fprintf('Properties (%d): %s\n', length(properties), strjoin(properties, ', '));
fprintf('\n');

%% Example 5: Working with Versioned Products

fprintf('=== Example 5: Accessing Versioned Properties ===\n');

% Access property from a specific version (v1, v2, etc.)
version_path = 'demo_workspace.demo_product.v1.demo_item.demo_sub_item.demo_property_mass';
value_v1 = poelis.get_value(version_path);
fprintf('Version 1 value: %.2f\n', value_v1);

% Access property from baseline version
baseline_path = 'demo_workspace.demo_product.baseline.demo_item.demo_sub_item.demo_property_mass';
value_baseline = poelis.get_value(baseline_path);
fprintf('Baseline value: %.2f\n', value_baseline);

% Access property from draft (current working version)
draft_path = 'demo_workspace.demo_product.draft.demo_item.demo_sub_item.demo_property_mass';
value_draft = poelis.get_value(draft_path);
fprintf('Draft value: %.2f\n', value_draft);

fprintf('\n');

%% Example 6: Updating Property Values

fprintf('=== Example 6: Updating Property Values ===\n');

% Note: Only draft properties can be updated. Versioned properties are read-only.

% Update a numeric property value
draft_property_path = 'demo_workspace.demo_product.draft.demo_item.demo_sub_item.demo_property_mass';
old_value = poelis.get_value(draft_property_path);
fprintf('Current value: %.2f\n', old_value);

% Update the value
new_value = 123.45;
poelis.change_property(draft_property_path, new_value, 'Updated mass', 'Changed mass value for testing');
fprintf('✓ Updated property value to %.2f\n', new_value);

% Verify the update
updated_value = poelis.get_value(draft_property_path);
fprintf('Verified value: %.2f\n', updated_value);
fprintf('\n');

% Update a text property
text_property_path = 'demo_workspace.demo_product.draft.demo_item.property_string';
poelis.change_property(text_property_path, 'New string text');
fprintf('✓ Updated text property\n');

