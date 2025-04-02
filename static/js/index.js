/* Przycisk do góry */
document.getElementById("up").addEventListener("click", function (event) {
    event.preventDefault();
    window.scrollTo({ top: 0, behavior: "smooth" });
});

document.addEventListener("DOMContentLoaded", async () => {
    const form = document.getElementById("listingForm");
    const typeSelect = document.getElementById("type");
    const categorySelect = document.getElementById("category");
    const filterCategorySelect = document.querySelector("#filter_form #category");
    const imageInput = document.querySelector("input[name='image'], input[name='image_edit']");

    // 📌 Dozwolone kolekcje
    const allowedCollections = ["renthings", "services", "products"];

    // 📌 Mapa stron do kolekcji
    const currentPath = window.location.pathname;

    let collectionToLoad = "all"; // Domyślnie załaduj wszystkie kategorie
    if (currentPath.includes("wypozyczalnia")) {
        collectionToLoad = "renthings";
    } else if (currentPath.includes("sklep")) {
        collectionToLoad = "products";
    } else if (currentPath.includes("uslugi")) {
        collectionToLoad = "services";
    } else if (currentPath.includes("edit_announcements")) {
        collectionToLoad = "all"; // Załaduj wszystko
    }

    if (!categorySelect && !filterCategorySelect) {
        console.error("❌ Nie znaleziono pola wyboru kategorii.");
        return;
    }

    // 📌 Tworzenie i dodanie podglądu zdjęcia
    let imagePreview;
    if (imageInput) {
        imagePreview = document.createElement("img");
        imagePreview.style.maxWidth = "200px";
        imagePreview.style.display = "none";
        imageInput.parentNode.insertBefore(imagePreview, imageInput.nextSibling);

        imageInput.addEventListener("change", (event) => {
            const file = event.target.files[0];

            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = "block";
                };
                reader.readAsDataURL(file);
            } else {
                imagePreview.style.display = "none";
            }
        });
    }

    // 📌 Tworzenie pola dla nowej nazwy dokumentu (na początku ukrytego)
    const newDocInput = document.createElement("input");
    if (newDocInput) {
        newDocInput.addEventListener("input", () => {
            newDocInput.value = newDocInput.value.toLowerCase();
        });
    }
    newDocInput.type = "text";
    newDocInput.name = "new_doc_name";
    newDocInput.id = "new_doc_name";
    newDocInput.classList.add("form-input");
    newDocInput.placeholder = "Wpisz nazwę nowego dokumentu";
    newDocInput.style.display = "none";

    if (categorySelect) categorySelect.insertAdjacentElement("afterend", newDocInput);

    // 📌 Funkcja do pobrania i załadowania kategorii
    async function loadCategories(collection, targetSelect) {
        if (!targetSelect) return;

        try {
            let categories = [];

            if (collection === "all") {
                let allCollections = ["renthings", "services", "products"];
                for (let coll of allCollections) {
                    let response = await fetch(`/get_document_names?collection=${coll}`);
                    if (response.ok) {
                        let data = await response.json();
                        if (Array.isArray(data) && data.length > 0) {
                            categories = categories.concat(data);
                        }
                    }
                }
            } else if (allowedCollections.includes(collection)) {
                let response = await fetch(`/get_document_names?collection=${collection}`);
                if (!response.ok) throw new Error("Błąd pobierania kategorii.");
                let data = await response.json();
                if (Array.isArray(data) && data.length > 0) {
                    categories = data;
                }
            } else {
                console.warn(`⚠️ Nieprawidłowa kolekcja: ${collection}`);
                targetSelect.innerHTML = '<option value="">Wszystkie</option>';
                return;
            }

            targetSelect.innerHTML = '<option value="">Wszystkie</option>';
            categories.forEach(category => {
                const option = document.createElement("option");
                option.value = category;
                option.textContent = category;
                targetSelect.appendChild(option);
            });

            if (targetSelect.id === "category" && form) {
                const otherOption = document.createElement("option");
                otherOption.value = "other";
                otherOption.textContent = "Inne";
                targetSelect.appendChild(otherOption);
            }
        } catch (error) {
            console.error("❌ Błąd ładowania kategorii:", error);
        }
    }

    // 📌 Obsługa zmiany kolekcji w formularzu dodawania ogłoszeń
    if (typeSelect) {
        typeSelect.addEventListener("change", function () {
            const selectedType = typeSelect.value;
            if (allowedCollections.includes(selectedType)) {
                loadCategories(selectedType, categorySelect);
            }
        });
    }

    // 📌 Obsługa zmiany kolekcji w filtrach
    const filterTypeSelect = document.querySelector("#filter_form #type");
    if (filterTypeSelect) {
        filterTypeSelect.addEventListener("change", function () {
            const selectedType = filterTypeSelect.value;
            if (allowedCollections.includes(selectedType)) {
                loadCategories(selectedType, filterCategorySelect);
            }
        });
    }

    // 📌 Obsługa opcji "Inne" w formularzu dodawania ogłoszeń
    if (categorySelect) {
        categorySelect.addEventListener("change", function () {
            if (categorySelect.value === "other") {
                newDocInput.style.display = "block";
                newDocInput.required = true;
            } else {
                newDocInput.style.display = "none";
                newDocInput.value = "";
                newDocInput.required = false;
            }
        });
    }

    // 📌 Załaduj domyślne kategorie przy starcie strony
    await loadCategories(collectionToLoad, filterCategorySelect);
    await loadCategories(collectionToLoad, categorySelect);

    function handleTypeChange(event, targetSelect) {
        const selectedType = event.target.value;
        if (allowedCollections.includes(selectedType)) {
            loadCategories(selectedType, targetSelect);
        }
    }

    if (typeSelect) {
        typeSelect.addEventListener("change", (event) => handleTypeChange(event, categorySelect));
    }

    const filterTypeSelect1 = document.querySelector("#filter_form #type");
    if (filterTypeSelect1) {
        filterTypeSelect1.addEventListener("change", (event) => handleTypeChange(event, filterCategorySelect));
    }

    // 📌 Walidacja formularza przed wysłaniem
    if (form) {
        form.addEventListener("submit", async function (event) {
            event.preventDefault();
            let isValid = true;

            const requiredFields = [
                "item_name", "desc", "deposit", "min_hours",
                "hour_to_day", "price_hour", "price_day", "producent", "piece"
            ];

            requiredFields.forEach((field) => {
                const input = document.querySelector(`[name="${field}"]`);
                if (input && input.value.trim() === "") {
                    isValid = false;
                    input.classList.add("error");
                    input.style.border = "2px solid red";
                } else {
                    input?.classList.remove("error");
                    input?.style.removeProperty("border");
                }
            });

            // 📌 Walidacja nowej nazwy dokumentu, gdy wybrano "Inne"
            if (categorySelect?.value === "other" && newDocInput.value.trim() === "") {
                isValid = false;
                newDocInput.style.border = "2px solid red";
                alert("Musisz podać nazwę nowego dokumentu.");
            } else {
                newDocInput.style.border = "";
            }

            if (!isValid) {
                alert("Proszę wypełnić wszystkie wymagane pola.");
                return;
            }

            // 📌 Wysyłanie formularza bez przeładowania strony (AJAX)
            try {
                const formData = new FormData(form);
                const response = await fetch("/add_announcement", {
                    method: "POST",
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    alert("Ogłoszenie dodane pomyślnie!");
                    form.reset();
                    if (imageInput) imagePreview.style.display = "none";
                    newDocInput.style.display = "none";
                } else {
                    alert(`Błąd: ${data.error}`);
                }
            } catch (error) {
                console.error("Błąd wysyłania formularza:", error);
                alert("Wystąpił problem z dodaniem ogłoszenia.");
            }
        });
    }
});


/*Dodawanie ogłoszeń*/
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById('filter_form');
    const itemsPerPage = 15;

    let currentPage = {
        renthings: 1,
        services: 1,
        products: 1
    };

    const scrollToTop = () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const scrollToBottom = () => {
        const paginationContainer = document.querySelector('article');
        if (paginationContainer) {
            paginationContainer.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    };



    const renderAnnouncements = (announcements, page, category) => {
        const container = document.getElementById(`announcements_${category}`);
        if (!container) return;

        container.innerHTML = "";

        const start = (page - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const paginatedAnnouncements = announcements.slice(start, end);

        if (paginatedAnnouncements.length === 0) {
            container.innerHTML = `<p class="no_items">Brak ogłoszeń pasujących do filtrów.</p>`;
        } else {
            paginatedAnnouncements.forEach(({ itemName, itemData, docId }) => {
                const announcementLink = document.createElement('a');
                announcementLink.classList.add('announcement');

                if (itemData.hidden == "1") return;
                const paramsList = itemData.parameters && typeof itemData.parameters === "object"
                    ? Object.entries(itemData.parameters).map(([key, value]) => `<li class="ad-params">${key}: ${value}</li>`).join('\n')
                    : '<li class="param">Brak dodatkowych informacji</li>';


                let announcementHTML = "";
                if (category === "renthings") {
                    announcementHTML = `
                        <a href="/details/${category}/${encodeURIComponent(docId)}/${encodeURIComponent(itemName)}" class="ad-container">
            <div class="ad-left">
                                <img src="${itemData.image || '../static/img/multi-fach_sklep.jpg'}" alt="${itemName}" class="ad-image">
                            </div>
                            <div class="ad-center">
                                <p class="item_name">${itemData.item_name || itemName}</p>
                                <p class="producent">${itemData.producent || 'Nieznany producent'}</p>
                                <p class="desc">${itemData.desc || 'Brak opisu'}</p>
                                <ul class="ad-params">
                                    ${paramsList}
                                </ul>
                            </div>
                            <div class="ad-right">
                                <p class="price_day">${itemData.price_day || 'N/A'} zł/doba</p>
                                <p class="price_hour">${itemData.price_hour || 'N/A'} zł/godzina</p>
                                <p class="hour_to_day">${itemData.hour_to_day || 'N/A'} godzin/y = cena doba</p>
                                <div class="transport_container">
    <b id="transport_word">Transport:</b> 
    <b class="${itemData.transport == 1 ? 'available' :
                            itemData.transport == 2 ? 'to_ask' :
                                itemData.transport == 0 ? 'no_available' :
                                    'not_specified'
                        }">
        ${itemData.transport == 1 ? 'Dostępny' :
                            itemData.transport == 2 ? 'Do uzgodnienia' :
                                itemData.transport == 0 ? 'Niedostępny' :
                                    'Nie określono'
                        }
    </b>
</div>

                                <p class="deposit"><b>Kaucja:</b> <b class="deposit_price">${itemData.deposit || 'N/A'} zł</b></p>
                                    <div class="available_container">
    <b id="available_word">Aktualnie:</b> 
    <b class="${itemData.available == 1 ? 'available' :
                            itemData.available == 2 ? 'to_ask' :
                                itemData.available == 0 ? 'no_available' :
                                    'not_specified'
                        }">
        ${itemData.available == 1 ? 'Dostępny' :
                            itemData.available == 2 ? 'Do uzgodnienia' :
                                itemData.available == 0 ? 'Niedostępny' :
                                    'Nie określono'
                        }
    </b>
</div>

                            </div>
                            <div class="rent_info">
                                <b class="strong_red">Pamiętaj</b>, że do podpisania <b class="strong_red">umowy</b> najmu będzie potrzebny <b class="strong_red">dowód osobisty</b> lub inny dokument potwierdzający tożsamość oraz <b class="strong_red">kaucja</b>.
                            </div>
                        </div>`;
                } else if (category === "services") {
                    announcementHTML = `
                        <a href="/details/${category}/${encodeURIComponent(docId)}/${encodeURIComponent(itemName)}" class="ad-container">
            <div class="ad-left">
                                <img src="${itemData.image || '../static/img/multi-fach_sklep.jpg'}" alt="${itemName}" class="ad-image">
                            </div>
                            <div class="ad-center">
                                <p class="item_name">${itemData.item_name || itemName}</p>
                                <p class="producent">${itemData.producent || 'Nieznany producent'}</p>
                                <p class="desc">${itemData.desc || 'Brak opisu'}</p>
                                <ul class="ad-params">
                                    ${paramsList}
                                </ul>
                            </div>
                            <div class="ad-right">
                                <p class="price_day">${itemData.price_day || 'N/A'} zł/doba</p>
                                <p class="price_hour">${itemData.price_hour || 'N/A'} zł/godzina</p>
                                <p class="service_min_hours">Minimalnie:</p><b class="service_min"> ${itemData.min_hours || 'N/A'} godzin/y</b>
                                <div class="transport_container">
    <b id="transport_word">Transport:</b> 
    <b class="${itemData.transport == 1 ? 'available' :
                            itemData.transport == 2 ? 'to_ask' :
                                itemData.transport == 0 ? 'no_available' :
                                    'not_specified'
                        }">
        ${itemData.transport == 1 ? 'Dostępny' :
                            itemData.transport == 2 ? 'Do uzgodnienia' :
                                itemData.transport == 0 ? 'Niedostępny' :
                                    'Nie określono'
                        }
    </b>
</div>

                                <div class="available_container">
    <b id="available_word">Aktualnie:</b><br>
    <b class="${itemData.available == 1 ? 'available' :
                            itemData.available == 2 ? 'to_ask' :
                                itemData.available == 0 ? 'no_available' :
                                    'not_specified'
                        }">
        ${itemData.available == 1 ? 'Dostępny' :
                            itemData.available == 2 ? 'Do uzgodnienia' :
                                itemData.available == 0 ? 'Niedostępny' :
                                    'Nie określono'
                        }
    </b>
</div>
                            </div>
                            <div class="rent_info">
                                <p class="info">Wystawiam fakturę VAT lub zwykły paragon.</p>
                            </div>
                        </div>`;
                } else if (category === "products") {
                    announcementHTML = `
                        <a href="/details/${category}/${encodeURIComponent(docId)}/${encodeURIComponent(itemName)}" class="ad-container">
            <div class="ad-left">
                                <img src="${itemData.image || '../static/img/multi-fach_sklep.jpg'}" alt="${itemName}" class="ad-image">
                            </div>
                            <div class="ad-center">
                                <p class="item_name">${itemData.item_name || itemName}</p>
                                <p class="producent">${itemData.producent || 'Nieznany producent'}</p>
                                <p class="desc">${itemData.desc || 'Brak opisu'}</p>
                                <ul class="ad-params">
                                    ${paramsList}
                                </ul>
                            </div>
                            <div class="ad-right">
                                <span class="price_day">Cena: </span><span class="price_day">${itemData.price_day || 'N/A'} zł/szt</span><br>
                                <span class="avai">Stan: </span><span class="price_hour">${itemData.piece || 'N/A'} szt</span>
                                <div class="available_container">
    <b id="available_word">Aktualnie:</b> 
    <b class="${itemData.available == 1 ? 'available' :
                            itemData.available == 2 ? 'to_ask' :
                                itemData.available == 0 ? 'no_available' :
                                    'not_specified'
                        }">
        ${itemData.available == 1 ? 'Dostępny' :
                            itemData.available == 2 ? 'Do uzgodnienia' :
                                itemData.available == 0 ? 'Niedostępny' :
                                    'Nie określono'
                        }
    </b>
</div>

                            </div>
                            <div class="rent_info">
                                <p class="info">Wystawiam fakturę VAT lub zwykły paragon.</p>
                            </div>
                        </div>`;
                }

                announcementLink.innerHTML = announcementHTML;
                container.appendChild(announcementLink);
            });
        }

        const totalPages = Math.ceil(announcements.length / itemsPerPage);

        const paginationContainer = document.createElement('div');
        paginationContainer.classList.add('pagination-buttons');

        const prevButton = document.createElement('button');
        prevButton.textContent = 'Poprzednia strona';
        prevButton.classList.add('load-more', 'previous_page_button');
        prevButton.addEventListener('click', () => {
            if (currentPage[category] > 1) {
                currentPage[category]--;
                renderAnnouncements(announcements, currentPage[category], category);
                scrollToBottom();
            }
        });

        const pageCounter = document.createElement('span');
        pageCounter.classList.add('page-counter');
        const totalPagesCategory = Math.max(1, Math.ceil(announcements.length / itemsPerPage));
        pageCounter.textContent = `Strona ${currentPage[category]} z ${totalPagesCategory}`;

        const loadMoreButton = document.createElement('button');
        loadMoreButton.textContent = 'Kolejna strona';
        loadMoreButton.classList.add('load-more', 'next_page_button');
        loadMoreButton.addEventListener('click', () => {
            if ((currentPage[category] * itemsPerPage) < announcements.length) {
                currentPage[category]++;
                renderAnnouncements(announcements, currentPage[category], category);
                scrollToTop();
            }
        });

        paginationContainer.appendChild(prevButton);
        paginationContainer.appendChild(pageCounter);
        paginationContainer.appendChild(loadMoreButton);
        container.appendChild(paginationContainer);
    };

    const fetchData = (collectionName) => {
        const formData = new FormData(form);
        const queryParams = new URLSearchParams(formData).toString();

        return fetch(`/${collectionName}_get?${queryParams}`)
            .then(response => response.json())
            .then(data => {
                if (!Array.isArray(data)) {
                    document.getElementById(`announcements_${collectionName}`).innerHTML = `<p>Błąd w pobranych danych.</p>`;
                    return [];
                }

                const processData = (data) => {
                    return data.reduce((acc, doc) => {
                        if (typeof doc !== 'object' || doc === null) return acc;

                        const selectedCategory = formData.get('category');
                        if (selectedCategory && doc.id !== selectedCategory) return acc;

                        Object.keys(doc).forEach(itemName => {
                            const itemData = doc[itemName];
                            if (itemName === "id" || typeof itemData !== 'object') return;

                            acc.push({
                                itemName,
                                itemData,
                                docId: doc.id,
                                category: doc.id,
                                collection: collectionName
                            });
                        });
                        return acc;
                    }, []);
                };

                let announcements = processData(data);

                // Filtr dostępności w JS
                const selectedAvailability = formData.get('availability');
                if (selectedAvailability) {
                    announcements = announcements.filter(ad => {
                        if (selectedAvailability === "available") return ad.itemData.available == 1;
                        if (selectedAvailability === "not_available") return ad.itemData.available == 0;
                        if (selectedAvailability === "to_ask") return ad.itemData.available == 2;
                        return true;
                    });
                }

                // Filtr widoczności w JS
                const selectedVisibility = formData.get('visibility_filter');
                if (selectedVisibility) {
                    announcements = announcements.filter(ad => {
                        if (selectedVisibility === "visible") return ad.itemData.hidden == "0";
                        if (selectedVisibility === "hidden") return ad.itemData.hidden == "1";
                        return true;
                    });
                }

                // Sortowanie według ceny
                const selectedSort = formData.get('price');
                if (selectedSort) {
                    announcements.sort((a, b) => {
                        const priceA = parseFloat(a.itemData.price_day || Infinity);
                        const priceB = parseFloat(b.itemData.price_day || Infinity);
                        return selectedSort === 'price_max' ? priceA - priceB : priceB - priceA;
                    });
                }

                // Przekazujemy przefiltrowane dane do renderowania
                renderAnnouncements(announcements, currentPage[collectionName], collectionName);
                return announcements;
            })
            .catch(error => {
                document.getElementById(`announcements_${collectionName}`).innerHTML = `<p>Błąd podczas ładowania danych: ${error.message}</p>`;
                return [];
            });
    };

    let currentPageAll = 1;

    const renderAllAnnouncements = (allAnnouncements) => {
        const container = document.getElementById("announcements_all");
        container.innerHTML = "";

        const start = (currentPageAll - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const paginatedAllAnnouncements = allAnnouncements.slice(start, end);

        if (paginatedAllAnnouncements.length === 0) {
            container.innerHTML = `<p class="no_items">Brak ogłoszeń pasujących do filtrów.</p>`;
        } else {
            paginatedAllAnnouncements.forEach(({ itemName, itemData, docId, category, collection }) => {
                const announcementLink = document.createElement('a');
                announcementLink.classList.add('announcement');

                const paramsList = itemData.parameters && typeof itemData.parameters === "object"
                    ? Object.entries(itemData.parameters)
                        .map(([key, value]) => `<li class="ad-params">${key}: ${value}</li>`)
                        .join('')
                    : '<li class="param">Brak dodatkowych informacji</li>';

                const announcementHTML = `
                    <a href="/edit_details/${collection}/${category}/${encodeURIComponent(itemName)}" class="ad-container">
            <div class="ad-left">
                            <img src="${itemData.image || '../static/img/multi-fach_sklep.jpg'}" alt="${itemName}" class="ad-image">
                        </div>
                        <div class="ad-center">
                            <p class="item_name">${itemData.item_name || itemName}</p>
                            <p class="category">Sekcja: ${collection === "renthings" ? "Wypożyczalnia" :
                        collection === "services" ? "Usługi" :
                            collection === "products" ? "Sklep" :
                                "Nieznana sekcja"
                    }</p>
                            <p class="category">Kategoria: ${category}</p>
                            <p class="desc">${itemData.desc || 'Brak opisu'}</p>
                            <ul class="ad-params">${paramsList}</ul>
    
                            <!-- Status widoczności ogłoszenia -->
                            <div class="visibility_container">
                                <b id="visibility_word">Status:</b> 
                                <b class="${itemData.hidden == '1' ? 'hidden-status' : 'visible-status'}">
                                    ${itemData.hidden == '1' ? 'Ukryte' : 'Widoczne'}
                                </b>
                            </div>
                        </div>
                        <div class="ad-right">
                            <b class="deposit_edit_price">Cena za dobę:</b><b class="price_day">${itemData.price_day || itemData.price || 'N/A'} zł</b><br>
                            <b class="deposit_edit_price">Cena za godzinę:</b><b class="price_day">${itemData.price_hour || 'N/A'} zł</b><br>
                            <b class="deposit_edit_price">Kaucja:</b> <b class="deposit_edit_price">${itemData.deposit || 'N/A'} zł</b><br>
                            <span class="avai">Stan: </span><span class="price_hour">${itemData.piece || 'N/A'} szt</span>
                            <p class="service_min_hours">Minimalnie:</p><b class="service_min"> ${itemData.min_hours || 'N/A'} godzin/y</b>
    
                            <div class="transport_container">
                                <b id="transport_word">Transport:</b> 
                                <b class="${itemData.transport == 1 ? 'available' :
                        itemData.transport == 2 ? 'to_ask' :
                            itemData.transport == 0 ? 'no_available' :
                                'not_specified'
                    }">
                                    ${itemData.transport == 1 ? 'Dostępny' :
                        itemData.transport == 2 ? 'Do uzgodnienia' :
                            itemData.transport == 0 ? 'Niedostępny' :
                                'Nie określono'
                    }
                                </b>
                            </div>
    
                            <div class="available_container">
                                <b id="available_word">Aktualnie:</b> 
                                <b class="${itemData.available == 1 ? 'available' :
                        itemData.available == 2 ? 'to_ask' :
                            itemData.available == 0 ? 'no_available' :
                                'not_specified'
                    }">
                                    ${itemData.available == 1 ? 'Dostępny' :
                        itemData.available == 2 ? 'Do uzgodnienia' :
                            itemData.available == 0 ? 'Niedostępny' :
                                'Nie określono'
                    }
                                </b>
                            </div>
                        </div>
                    </div>`;

                // Dodanie kodu do kontenera
                announcementLink.innerHTML = announcementHTML;
                container.innerHTML += announcementLink.outerHTML;
            });
        }

        const totalPages = Math.ceil(allAnnouncements.length / itemsPerPage);

        const paginationContainer = document.createElement('div');
        paginationContainer.classList.add('pagination-buttons');

        const prevButton = document.createElement('button');
        prevButton.textContent = 'Poprzednia strona';
        prevButton.classList.add('load-more', 'previous_page_button');
        prevButton.addEventListener('click', () => {
            if (currentPageAll > 1) {
                currentPageAll--;
                renderAllAnnouncements(allAnnouncements);
                scrollToBottom();
            }
        });

        const nextButton = document.createElement('button');
        nextButton.textContent = 'Kolejna strona';
        nextButton.classList.add('load-more', 'next_page_button');
        nextButton.addEventListener('click', () => {
            if ((currentPageAll * itemsPerPage) < allAnnouncements.length) {
                currentPageAll++;
                renderAllAnnouncements(allAnnouncements);
                scrollToTop();
            }
        });

        const pageCounter = document.createElement('span');
        pageCounter.classList.add('page-counter');
        const totalPages1 = Math.max(1, Math.ceil(allAnnouncements.length / itemsPerPage));
        pageCounter.textContent = `Strona ${currentPageAll} z ${totalPages1}`;

        paginationContainer.appendChild(prevButton);
        paginationContainer.appendChild(pageCounter);
        paginationContainer.appendChild(nextButton);
        container.appendChild(paginationContainer);
    };



    const fetchAllData = () => {
        const formDataObj = new FormData(form);
        const selectedType = formDataObj.get('type');

        let fetchPromises = [];

        if (selectedType) {
            fetchPromises.push(fetchData(selectedType));
        } else {
            fetchPromises = [
                fetchData('renthings'),
                fetchData('services'),
                fetchData('products')
            ];
        }

        Promise.all(fetchPromises).then(results => {
            const combinedAnnouncements = results.flat();

            // ❗ Nie filtrujemy hidden, żeby pokazać WSZYSTKIE ogłoszenia
            renderAllAnnouncements(combinedAnnouncements);
        });
    };


    form.addEventListener('submit', event => {
        event.preventDefault();
        currentPage = { renthings: 1, services: 1, products: 1 };
        fetchAllData();
    });

    fetchAllData();
});

/*Przycisk więcej*/
document.getElementById("mobile_section").addEventListener("click", function (event) {
    event.preventDefault();
    document.getElementById("taget_position").scrollIntoView({
        behavior: "smooth"
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const textarea = document.getElementById("parameters");

    const adjustHeight = () => {
        textarea.style.height = "auto";
        textarea.style.height = (textarea.scrollHeight) + "px";
    };

    adjustHeight();

    textarea.addEventListener("input", adjustHeight);
});


function confirmVisibilityChange() {
    const selectElement = document.getElementById('hidden');
    const selectedValue = selectElement.value;

    if (selectedValue === "1") {
        const confirmHide = confirm("Czy na pewno chcesz ukryć to ogłoszenie?");
        if (!confirmHide) {
            selectElement.value = "0"; // Cofnięcie zmiany
        }
    } else if (selectedValue === "0") {
        const confirmShow = confirm("Czy na pewno chcesz, aby to ogłoszenie było ponownie widoczne?");
        if (!confirmShow) {
            selectElement.value = "1"; // Cofnięcie zmiany
        }
    }
}
// Wczytanie podglądu obrazu
document.addEventListener("DOMContentLoaded", async () => {
    const imageInput = document.querySelector("input[name='image'], input[name='image_edit']");

    if (imageInput) {
        let imagePreview = document.querySelector("#preview-image");

        // Jeśli podgląd nie istnieje, twórz nowy
        if (!imagePreview) {
            imagePreview = document.createElement("img");
            imagePreview.id = "preview-image";
            imagePreview.style.maxWidth = "200px";
            imagePreview.style.display = "none";
            imagePreview.style.marginTop = "10px";

            imageInput.parentNode.insertBefore(imagePreview, imageInput.nextSibling);
        }

        imageInput.addEventListener("change", function (event) {
            const file = event.target.files[0];

            if (file) {
                // 📌 **Sprawdzenie formatu pliku**
                const allowedTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
                if (!allowedTypes.includes(file.type)) {
                    alert("❌ Proszę wybrać plik graficzny w formacie JPG, PNG, GIF lub WEBP.");
                    event.target.value = "";
                    return;
                }

                // 📌 **Sprawdzenie rozmiaru pliku (2MB)**
                const maxSize = 2 * 1024 * 1024;
                if (file.size > maxSize) {
                    alert("❌ Rozmiar pliku jest zbyt duży. Maksymalny dopuszczalny rozmiar to 2MB.");
                    event.target.value = "";
                    return;
                }

                // 📌 **Czytanie pliku i ustawienie podglądu**
                const reader = new FileReader();
                reader.onload = function (e) {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = "block";
                };
                reader.readAsDataURL(file);
            } else {
                imagePreview.style.display = "none";
            }
        });
    }
});

const uploadFile = async (file) => {
    const storageRef = firebase.storage().ref();
    const fileRef = storageRef.child(`images/${file.name}`);

    await fileRef.put(file);
    return await fileRef.getDownloadURL();
};
// Domyślne wartości
const defaultSubject = "Zapytanie ze strony";
const defaultMessage = "Dzień dobry,\n\nPozdrawiam.";

// Przywracanie domyślnego tematu, jeśli użytkownik je usunie
document.getElementById("subject").addEventListener("blur", function () {
    if (this.value.trim() === "") {
        this.value = defaultSubject;
    }
});

// Przywracanie domyślnej treści wiadomości, jeśli użytkownik jej nie zmieni
document.getElementById("message").addEventListener("blur", function () {
    if (this.value.trim() === "") {
        this.value = defaultMessage;
    }
});

document.addEventListener("DOMContentLoaded", function () {
    const select = document.getElementById("subject");
    const customSubjectGroup = document.getElementById("custom-subject-group");
    const customSubjectInput = document.getElementById("custom-subject");

    // Pobierz tematy z backendu
    fetch("/get_subjects")
        .then(response => response.json())
        .then(subjects => {
            subjects.forEach(subject => {
                let option = document.createElement("option");
                option.value = subject;
                option.textContent = subject;
                select.appendChild(option);
            });
        })
        .catch(error => console.error("Błąd podczas pobierania tematów:", error));

    // Obsługa zmiany opcji w select
    select.addEventListener("change", function () {
        if (select.value === "Inne zapytanie") {
            customSubjectGroup.style.display = "block"; // Pokazuje pole do wpisania tematu
            customSubjectInput.required = true; // Wymusza wpisanie tematu
        } else {
            customSubjectGroup.style.display = "none"; // Ukrywa pole
            customSubjectInput.required = false; // Nie wymaga wpisania tematu
        }
    });
});