console.log('Using base.js');

// Grab info for determining active page
let currentPath = window.location.pathname;
let trimmedPath = currentPath.split('/')[1];
let navLinks = document.querySelectorAll('.sidebar-links');

// Compare current path with nav links to determine active page
for (let link of navLinks) {
  let href = link.getAttribute('href');
  if (href.includes(trimmedPath)) {
    link.classList.add('active');
  }
}

// Grab nav item elements for resizing
let grid = document.getElementsByClassName('grid')[0];
let logoDiv = document.getElementById('logo');
let logoImg = document.querySelectorAll('img[alt="Track My Dollars Logo"]')[0];
let collapseIcon = document.getElementsByClassName('nav-collapse')[0];

let dashboardLink;
let assetsDebtsLink;
let moneyScheduleLink;
let budgetLink;
let reportsLink;
let offersLink;
let supportLink;
let settingsLink;
let logoutLink;

function getNavLinks() {
  dashboardLink = document.querySelectorAll('a[href="/dashboard/"]')[0];
  assetsDebtsLink = document.querySelectorAll('a[href="/assets-debts/"]')[0];
  moneyScheduleLink = document.querySelectorAll('a[href="/money-schedule/"]')[0];
  budgetLink = document.querySelectorAll('a[href="/budget/"]')[0];
  reportsLink = document.querySelectorAll('a[href="/reports/"]')[0];
  offersLink = document.querySelectorAll('a[href="/offers/"]')[0];
  supportLink = document.querySelectorAll('a[href="/support/"]')[0];
  settingsLink = document.querySelectorAll('a[href="/settings"]')[0];
  logoutLink = document.querySelectorAll('a[href="/accounts/logout/"]')[0];
}

// Collapses side nav
function collapseNav() {
  console.log('Collapsing nav');
  collapseIcon.classList.remove('fa-circle-chevron-left');
  collapseIcon.classList.add('fa-circle-chevron-right');

  // TODO: Shrink side nav - reduce size and change text to images
  grid.style.gridTemplateColumns = '80px 5fr 2fr';
  collapseIcon.style.left = '72px';

  getNavLinks();

  logoDiv.style.margin = '16px 2px';
  logoImg.style.maxWidth = '76px';
  dashboardLink.innerHTML = '<i class="fa-solid fa-gauge-high" title="Dashboard" style="font-size: 20px; width: 100%; text-align: center;"></i>';
  assetsDebtsLink.innerHTML = '<i class="fa-solid fa-scale-unbalanced-flip" title="Assets & Debts" style="font-size: 20px; width: 100%; text-align: center;"></i>';
  moneyScheduleLink.innerHTML = '<i class="fa-solid fa-calendar" title="Money Schedule" style="font-size: 20px; width: 100%; text-align: center;"></i>';
  budgetLink.innerHTML = '<i class="fa-solid fa-piggy-bank" title="Budget" style="font-size: 20px; width: 100%; text-align: center;"></i>';
  reportsLink.innerHTML = '<i class="fa-solid fa-chart-simple" title="Reports" style="font-size: 20px; width: 100%; text-align: center;"></i>';
  offersLink.innerHTML = '<i class="fa-solid fa-hand-holding-dollar" title="Offers" style="font-size: 20px; width: 100%; text-align: center;"></i>';
  supportLink.innerHTML = '<i class="fa-solid fa-circle-question" title="Support" style="font-size: 20px; width: 100%; text-align: center;"></i>';
  settingsLink.innerHTML = '<i class="fa-solid fa-user" title="Settings" style="font-size: 20px; margin: 8px 15px; text-align: center;"></i>';
  logoutLink.innerHTML = '<i class="fa-solid fa-door-open" title="Logout" style="font-size: 20px; margin: 8px 15px; text-align: center;"></i>';
}

// Expands side nav
function expandNav() {
  console.log('Expanding nav');
  collapseIcon.classList.remove('fa-circle-chevron-right');
  collapseIcon.classList.add('fa-circle-chevron-left');

  // TODO: Expand side nav - increase size and change images to text
  grid.style.gridTemplateColumns = '185px 5fr 2fr';
  collapseIcon.style.left = '177px';
}

// Expands or collapses side nav according to session variable
function adjustNav() {
  fetch('http://127.0.0.1:8000/session/nav_collapsed/get', {
    method: "GET",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    }
  })
  .then(response => response.json())
  .then(data => {
    if ('nav_collapsed' in data && data.nav_collapsed) {
      collapseNav();
    } else {
      expandNav();
    }
  });
}

adjustNav();

// Listens for click of an icon and triggers the nav bar to be adjusted
collapseIcon.addEventListener('click', function () {
  fetch('http://127.0.0.1:8000/session/nav_collapsed/toggle', {
    method: "GET",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    }
  })
  .then(response => response.json())
  .then(data => {
    adjustNav()
  });
});

// Add hover effect for icon
collapseIcon.addEventListener('mouseover', function () {
  collapseIcon.classList.add('fa-beat');
});

// Remove hover effect for icon
collapseIcon.addEventListener('mouseleave', function () {
  collapseIcon.classList.remove('fa-beat');
});