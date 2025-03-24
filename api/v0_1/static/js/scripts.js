document.getElementById('download-button').addEventListener('click', async () => {
    const selectedNode = document.querySelector('.jstree-node.selected');

    if (!selectedNode) {
        alert("Please select a file or folder to download.");
        return;
    }

    const selectedEndpointElement = selectedNode.closest('.endpoint_url');
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

document.addEventListener("DOMContentLoaded", function() {
  console.log("scripts.js loaded");
});

// Function to handle form submission for endpoint creation
function handleSubmit(event) {
  event.preventDefault();
  console.log("handleSubmit triggered");

  const form = event.target;
  console.log("Processing form for flavour:", form.dataset.flavour);

  // Build a JSON object from the form data
  const formData = new FormData(form);
  const data = {};
  formData.forEach((value, key) => {
    data[key] = value;
  });
  console.log("Sending payload:", data);

  // Send the JSON payload via fetch() to POST /endpoints/
  fetch("/admin/endpoints/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  })
  .then(response => {
    if (!response.ok) {
      return response.json().then(err => { throw err; });
    }
    return response.json();
  })
  .then(result => {
    alert("Endpoint created successfully: " + result.detail);
    // Optionally refresh the page or update the endpoint list in the UI
  })
  .catch(err => {
    alert("Error: " + (err.detail || JSON.stringify(err)));
  });

  return false;
}

// Function to toggle the display of the creation form for a given flavour
function toggleForm(flavour) {
  var formDiv = document.getElementById('form-' + flavour);
  if (formDiv.style.display === 'none' || formDiv.style.display === '') {
    formDiv.style.display = 'block';
  } else {
    formDiv.style.display = 'none';
  }
}

function deleteEndpoint(endpointId) {
  if (confirm("Are you sure you want to delete this endpoint?")) {
    // Update the URL to include the '/admin' prefix if needed.
    fetch("/admin/endpoints/?endpoint_uid=" + encodeURIComponent(endpointId), {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json"
      }
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(err => { throw err; });
      }
      return response.json();
    })
    .then(result => {
      alert("Endpoint deleted successfully: " + result.detail);
      // Optionally remove the endpoint card from the UI
      var card = document.getElementById("card-" + endpointId);
      if (card) {
        card.parentNode.removeChild(card);
      }
    })
    .catch(err => {
      alert("Error deleting endpoint: " + (err.detail || JSON.stringify(err)));
    });
  }
}

