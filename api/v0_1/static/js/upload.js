document.addEventListener('DOMContentLoaded', () => {
    console.log('assetsData:', assetsData); // Debug the assetsData

    Object.entries(assetsData).forEach(([endpoint, items], index) => {
        console.log(`Initializing jstree for endpoint: ${endpoint}, items:`, items);

        $('#tree-' + index).jstree({
            'core': {
                'data': items
            }
        }).on('select_node.jstree', function (e, data) {
            $('.jstree-node').removeClass('selected');
            $(`[data-id='${data.node.id}']`).addClass('selected');
        });

        // Check if the tree container is rendered
        console.log(`Tree container for #tree-${index}:`, $('#tree-' + index));
    });
});

document.getElementById('upload-button').addEventListener('click', async () => {
    const selectedNode = document.querySelector('.jstree-node.selected');

    if (!selectedNode) {
        alert("Please select a destination folder.");
        return;
    }

    const selectedEndpointElement = selectedNode.closest('.endpoint');
    if (!selectedEndpointElement) {
        alert("Endpoint not found.");
        return;
    }

    const selectedEndpoint = selectedEndpointElement.dataset.endpoint;
    const destinationPath = selectedNode.dataset.id;
    const files = document.getElementById('file-input').files;

    if (files.length === 0) {
        alert("Please select files to upload.");
        return;
    }

    console.log(`Selected Endpoint: ${selectedEndpoint}`);
    console.log(`Destination Path: ${destinationPath}`);
    console.log('Files:', files);

    try {
        for (const file of files) {
            const uploadPath = `${destinationPath}/${file.webkitRelativePath || file.name}`;
            console.log(`Uploading file to: ${uploadPath}`);
            console.log('File details:', file);

            // Check if uploadPath is correctly defined
            if (!uploadPath || uploadPath.includes('undefined')) {
                console.error('uploadPath is undefined or empty:', uploadPath);
                continue;
            }

            const presignedUrlResponse = await fetch(`/assets/upload?resource=${encodeURIComponent(uploadPath)}&access_point=${encodeURIComponent(selectedEndpoint)}`, {
                method: 'PUT',
                credentials: 'include'
            });

            if (!presignedUrlResponse.ok) {
                throw new Error('Failed to get presigned URL for ' + uploadPath);
            }

            const { presigned_url } = await presignedUrlResponse.json();
            console.log(`Presigned URL for ${file.name}: ${presigned_url}`);
            const uploadResponse = await fetch(presigned_url, {
                method: 'PUT',
                body: file
            });

            if (!uploadResponse.ok) {
                throw new Error(`Failed to upload ${file.name}`);
            }

            console.log(`Uploaded file: ${file.name}`);
        }

        alert('Files uploaded successfully.');
    } catch (error) {
        console.error('Error uploading files:', error);
        alert('An error occurred while uploading the files.');
    }
});
