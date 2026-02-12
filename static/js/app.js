const toggleButton = document.getElementById('toggle-btn')
const sidebar = document.getElementById('sidebar')
const submenu = document.getElementById('sub-menu')

function toggleSidebar(){
    sidebar.classList.toggle('close')
    toggleButton.classList.toggle('rotate')

    closeAllSubMenus()
}

function toggleSubMenu(button){
    
    if(!button.nextElementSibling.classList.contains('show')){
        closeAllSubMenus()
    }
    
    /*Con nextElementSibling accediamo all'elemento html successivo al bottone, ovvero il submenu*/
    button.nextElementSibling.classList.toggle('show')
    button.classList.toggle('rotate')

    if (sidebar.classList.contains('close')){
        sidebar.classList.toggle('close')
        toggleButton.classList.toggle('rotate')
    }
}

function closeAllSubMenus(){
    Array.from(sidebar.getElementsByClassName('show')).forEach(ul => {
        ul.classList.remove('show')
        ul.previousElementSibling.classList.remove('rotate')
    })
}
