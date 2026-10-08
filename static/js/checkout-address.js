(() => {
    const dataElement = document.getElementById('nepal-location-data');
    const provinceField = document.getElementById('id_province');
    const districtField = document.getElementById('id_district');
    const municipalityField = document.getElementById('id_municipality');
    if (!dataElement || !provinceField || !districtField || !municipalityField) return;

    const locations = JSON.parse(dataElement.textContent);
    const setOptions = (field, values, placeholder) => {
        field.replaceChildren(new Option(placeholder, ''));
        values.forEach((value) => field.add(new Option(value, value)));
    };

    provinceField.addEventListener('change', () => {
        setOptions(districtField, Object.keys(locations[provinceField.value] || {}), 'Select district');
        setOptions(municipalityField, [], 'Select municipality or rural municipality');
    });
    districtField.addEventListener('change', () => {
        const municipalities = locations[provinceField.value]?.[districtField.value] || [];
        setOptions(municipalityField, municipalities, 'Select municipality or rural municipality');
    });
})();
