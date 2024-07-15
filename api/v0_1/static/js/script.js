document.getElementById('download-button').addEventListener('click', async () => {
    const selectedNode = document.querySelector('.jstree-node.selected');

    if (!selectedNode) {
        alert("Please select a file or folder to download.");
        return;
    }

    const selectedEndpointElement = selectedNode.closest('.endpoint');
    if (!selectedEndpointElement) {
        alert("Endpoint not found.");
        return;
    }

    const selectedEndpoint = selectedEndpointElement.dataset.endpoint;
    const resource = selectedNode.dataset.id;

    try {
        const presignedUrlResponse = await fetch(`/assets/download?resource=${encodeURIComponent(resource)}&access_point=${encodeURIComponent(selectedEndpoint)}`, {
            method: 'PUT',
            credentials: 'include'
        });

        if (!presignedUrlResponse.ok) {
            throw new Error('Failed to get presigned URL for ' + resource);
        }

        const { presigned_urls, file_paths } = await presignedUrlResponse.json();
        console.log('Presigned URLs:', presigned_urls);
        console.log('File paths:', file_paths);

        if (presigned_urls.length !== file_paths.length) {
            throw new Error('Mismatch between presigned URLs and file paths.');
        }

        const zip = new JSZip();
        const fetchPromises = presigned_urls.map((url, index) => {
            console.log(`Fetching file: ${file_paths[index]} from URL: ${url}`);
            return fetch(url, { mode: 'cors' }).then(response => {
                if (response.ok) {
                    return response.blob();
                }
                console.error(`Error fetching ${url}: ${response.statusText}`);
                throw new Error(`Error fetching ${url}: ${response.statusText}`);
            }).then(blob => {
                console.log(`Fetched file: ${file_paths[index]} with size: ${blob.size}`);
                zip.file(file_paths[index], blob);
            }).catch(error => {
                console.error(`Error fetching ${url}:`, error);
            });
        });

        await Promise.all(fetchPromises);
        zip.generateAsync({ type: 'blob' }).then((content) => {
            saveAs(content, 'download.zip');
        }).catch((err) => {
            console.error('Error generating ZIP file:', err);
        });
    } catch (error) {
        console.error('Error processing fetch promises:', error);
        alert('An error occurred while downloading the files. Please try again.');
    }
});
