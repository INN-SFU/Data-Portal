self.addEventListener('fetch', event => {
  // Generalize the condition to match any presigned URL pattern
  if (event.request.url.includes('AWSAccessKeyId') && event.request.url.includes('Signature')) {
    event.respondWith(fetch(event.request));
  }
});
