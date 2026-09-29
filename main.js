function tabNav() {
  const tab_menu = document.querySelectorAll(".js-tabmenu li");
  const tab_content = document.querySelectorAll(".js-tabcontent section");
  tab_content[0].classList.add("ativo");

  if (tab_menu.length > 0 && tab_content.length > 0) {
    function tabAtiva(index) {
      tab_content.forEach((item) => {
        item.classList.remove("ativo");
      });
      tab_content[index].classList.add("ativo");
    }

    tab_menu.forEach((i, index) => {
      i.addEventListener("click", function () {
        tabAtiva(index);
      });
    });
  }
}
tabNav();

function accordionNav() {
  const accordion_list = document.querySelectorAll(".js-accordion dt");

  if (accordion_list.length > 0) {
    function accordionAtivo() {
      this.classList.toggle("ativo");
      this.nextElementSibling.classList.toggle("ativo");
    }

    accordion_list.forEach((i) => {
      i.addEventListener("click", accordionAtivo);
    });
  }
}
accordionNav();

function smoothScroll() {
  const links_internos = document.querySelectorAll(".js-menu a[href^='#']");

  function scrollSection(event) {
    event.preventDefault();
    const href = event.currentTarget.getAttribute("href");
    const section = document.querySelector(href);

    section.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  links_internos.forEach((i) => {
    i.addEventListener("click", scrollSection);
  });
}
smoothScroll();

function scrollAnimation() {
  const sections = document.querySelectorAll(".js-scroll");

  function animaScroll() {
    sections.forEach((i) => {
      const topo = i.getBoundingClientRect().top;
      const isSectionVisible = topo - window.innerHeight * 0.6 < 0;
      if (isSectionVisible) {
        i.classList.add("ativo");
      }
    });
  }

  animaScroll();

  window.addEventListener("scroll", animaScroll);
}
scrollAnimation();
