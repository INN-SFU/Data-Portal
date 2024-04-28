<script>
document.addEventListener("DOMContentLoaded", function() {
    var folders = document.querySelectorAll('.folder');
    folders.forEach(function(folder) {
        folder.addEventListener('click', function(event) {
            event.stopPropagation(); // Prevents the event from bubbling up to parent elements
            var childUl = this.querySelector('ul');
            if (childUl.style.display === 'block') {
                childUl.style.display = 'none';
            } else {
                childUl.style.display = 'block';
            }
        });
    });
});
</script>
