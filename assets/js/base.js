console.log('Using base.js');

// Grab nav item elements for resizing
let grid = document.getElementsByClassName('grid')[0];

// Header elements
let navDiv = document.getElementsByTagName('nav')[0];
let logoDiv = document.getElementById('logo');
let logoImg = document.querySelectorAll('img[alt="Track My Dollars Logo"]')[0];
let collapseIcon = document.getElementsByClassName('nav-collapse')[0];

// Nav links
let dashboardLink;
let assetsDebtsLink;
let moneyScheduleLink;
let budgetLink;
let reportsLink;
let offersLink;
let supportLink;
let settingsLink;
let logoutLink;

// Refresh variables that point to various nav links
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

const PAGE_LIST = [
  {
    'name': 'Dashboard',
    'href': '/dashboard/',
    'icon': 'fa-gauge-high'
  },
  {
    'name': 'Assets & Debts',
    'href': '/assets-debts/',
    'icon': 'fa-scale-unbalanced-flip'
  },
  {
    'name': 'Money Schedule',
    'href': '/money-schedule/',
    'icon': 'fa-calendar'
  },
  {
    'name': 'Budget',
    'href': '/budget/',
    'icon': 'fa-piggy-bank'
  },
  {
    'name': 'Reports',
    'href': '/reports/',
    'icon': 'fa-chart-simple'
  },
  {
    'name': 'Offers',
    'href': '/offers/',
    'icon': 'fa-hand-holding-dollar'
  },
  {
    'name': 'Support',
    'href': '/support/',
    'icon': 'fa-circle-question'
  },
]

// Checks session variable to see if the nav bar should be collapsed
async function isNavCollapsed() {
  let response = await fetch('http://127.0.0.1:8000/session/nav_collapsed/get');
  let data = await response.json();
  return data['nav_collapsed'];
}

// Creates the side nav on page refresh
async function createNav() {
  let collapse = await isNavCollapsed();

  logoImg.style.display = 'inherit';

  // Create nav links
  for (let page of PAGE_LIST) {
    let aEl = document.createElement('a');
    aEl.href = page.href;
    aEl.classList.add('sidebar-links');
    navDiv.append(aEl);
  }

  collapse? collapseNav(): expandNav();
  setActivePage();
}

createNav()

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
  dashboardLink.innerHTML = `<i class="fa-solid fa-gauge-high" title="Dashboard"=></i>`;
  assetsDebtsLink.innerHTML = `<i class="fa-solid fa-scale-unbalanced-flip" title="Assets & Debts"=></i>`;
  moneyScheduleLink.innerHTML = `<i class="fa-solid fa-calendar" title="Money Schedule"=></i>`;
  budgetLink.innerHTML = `<i class="fa-solid fa-piggy-bank" title="Budget"=></i>`;
  reportsLink.innerHTML = `<i class="fa-solid fa-chart-simple" title="Reports"=></i>`;
  offersLink.innerHTML = `<i class="fa-solid fa-hand-holding-dollar" title="Offers"=></i>`;
  supportLink.innerHTML = `<i class="fa-solid fa-circle-question" title="Support"=></i>`;
  settingsLink.innerHTML =`<i class="fa-solid fa-user" title="Settings" style="font-size: 20px; margin: 8px 15px; text-align: center;"></i>`;
  logoutLink.innerHTML = `<i class="fa-solid fa-door-open" title="Logout" style="font-size: 20px; margin: 8px 15px; text-align: center;"></i>`;
}

// Expands side nav
function expandNav() {
  console.log('Expanding nav');
  collapseIcon.classList.remove('fa-circle-chevron-right');
  collapseIcon.classList.add('fa-circle-chevron-left');

  getNavLinks();

  grid.style.gridTemplateColumns = '185px 5fr 2fr';

  logoDiv.style.margin = '28px 16px 10px 16px;';
  logoImg.style.maxWidth = '150px';

  collapseIcon.style.left = '177px';
  dashboardLink.innerText = 'Dashboard';
  assetsDebtsLink.innerText = 'Assets & Debts';
  moneyScheduleLink.innerText = 'Money Schedule'
  budgetLink.innerText = 'Budget';
  reportsLink.innerText = 'Reports';
  offersLink.innerText = 'Offers';
  supportLink.innerText = 'Support';
  settingsLink.innerText = settingsLink.getAttribute('title')
  logoutLink.innerText = 'Log Out';
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

function setActivePage() {
  console.log('Attempting to set active page');
  // Grab info for determining active page
  let currentPath = window.location.pathname;
  let trimmedPath = currentPath.split('/')[1];
  let navLinks = document.querySelectorAll('.sidebar-links');
  console.log(navLinks);
  // Compare current path with nav links to determine active page
  for (let link of navLinks) {
    console.log('Link');
    console.log(link);
    let href = link.getAttribute('href');
    if (href.includes(trimmedPath)) {
      link.classList.add('active');
    }
  }
}

const mqLarge  = window.matchMedia( '(min-width: 768px)' );
mqLarge.addEventListener('change', mqHandler);

// media query handler function
async function mqHandler(e) {
  if (e.matches) {

    grid.style.gridTemplateColumns = await isNavCollapsed() ?
      '80px 5fr 2fr':
      '185px 5fr 2fr';
  } else {
    console.log('Small - settings to auto')
    grid.style.gridTemplateColumns = 'auto';
  }
  console.log(
    e.matches ? 'large' : 'not large'
  );

}