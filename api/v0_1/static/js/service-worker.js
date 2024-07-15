self.addEventListener('fetch', function(event) {
    event.respondWith(
        fetch(event.request).then(function(response) {
            if (response.ok) {
                return response.blob().then(function(blob) {
                    return new Response(blob, {
                        headers: response.headers
                    });
                });
            }
            return response;
        }).catch(function(error) {
            console.error('Fetching failed:', error);
            throw error;
        })
    );
});
