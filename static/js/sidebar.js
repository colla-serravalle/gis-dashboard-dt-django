document.addEventListener("DOMContentLoaded", function () {
    var currentPath = window.location.pathname;
    var menuLinks = document.querySelectorAll("#sidebar ul li a");

    menuLinks.forEach(function (link) {
        var linkPath = link.getAttribute("href");
        if (currentPath === linkPath) {
            menuLinks.forEach(function (item) {
                item.parentElement.classList.remove("active");
            });
            link.parentElement.classList.add("active");
        }
    });
});
