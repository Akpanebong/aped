
/* ==========================================================================
   APED MONITORING SYSTEM
   DYNAMIC MONITORING FORM BUILDER
   Version: 2.0
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    'use strict';

    /* ==============================================================
       1. DOM ELEMENTS
       ============================================================== */

    const builder = document.getElementById('schema-builder');
    const emptyState = document.getElementById('schema-empty');
    const hiddenSchema = document.getElementById('id_schema');
    const schemaData = document.getElementById('schema-data');
    const definitionForm = document.getElementById('definition-form');

    if (!builder || !hiddenSchema || !definitionForm) {
        return;
    }

    const buttons = {
        addTop: document.getElementById('add-section'),
        addBottom: document.getElementById('add-section-bottom'),
        addFirst: document.getElementById('add-first-section')
    };


    /* ==============================================================
       2. CONFIGURATION
       ============================================================== */

    const FIELD_TYPES = [
        { value: 'text', label: 'Short text' },
        { value: 'textarea', label: 'Long text' },
        { value: 'number', label: 'Number' },
        { value: 'date', label: 'Date' },
        { value: 'select', label: 'Dropdown' },
        { value: 'linked_record', label: 'Linked record' }
    ];

    const LINKED_SOURCES = [
        ['project', 'Projects'],
        ['activity', 'Programme activities'],
        ['field_attendance', 'Attendance sheets'],
        ['field_attendance_participant', 'Attendance participants'],
        ['monitoring_record', 'Monitoring records'],
        ['follow_up_action', 'Follow-up actions'],
        ['vsla_group', 'VSLA groups'],
        ['vsla_member', 'VSLA members'],
        ['vsla_meeting', 'VSLA meetings'],
        ['vsla_meeting_attendance', 'VSLA meeting attendance'],
        ['vsla_savings_transaction', 'VSLA savings transactions'],
        ['vsla_loan', 'VSLA loans'],
        ['vsla_loan_repayment', 'VSLA loan repayments'],
        ['vsla_social_fund_transaction', 'VSLA social fund transactions'],
        ['vsla_challenge_story', 'VSLA challenge and success stories']
    ];

    const DEFAULT_FIELD = {
        label: '',
        type: 'text',
        required: false,
        choices: []
    };

    const DEFAULT_SECTION = {
        title: '',
        repeatable: false,
        fields: [{ ...DEFAULT_FIELD }]
    };


    /* ==============================================================
       3. UTILITIES
       ============================================================== */

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>"']/g, char => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        })[char]);
    }

    function parseInitialSchema() {
        if (!schemaData) return [];

        try {
            const parsed = JSON.parse(
                schemaData.textContent || '[]'
            );

            return Array.isArray(parsed) ? parsed : [];

        } catch (error) {
            console.error(
                'APED: Unable to load initial form schema.',
                error
            );

            return [];
        }
    }

    function getFieldType(type) {
        return FIELD_TYPES.some(item => item.value === type)
            ? type
            : 'text';
    }

    function parseChoices(value) {
        return String(value || '')
            .split(',')
            .map(choice => choice.trim())
            .filter(Boolean);
    }

    function createId(prefix) {
        return `${prefix}-${crypto.randomUUID
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
    }


    /* ==============================================================
       4. FIELD TEMPLATE
       ============================================================== */

    function fieldTemplate(field = {}) {
        const type = getFieldType(field.type);
        const choices = Array.isArray(field.choices)
            ? field.choices.join(', ')
            : '';
        const linkedModel = field.linked_model || 'field_attendance';

        const options = FIELD_TYPES.map(item => `
            <option
                value="${item.value}"
                ${item.value === type ? 'selected' : ''}
            >
                ${item.label}
            </option>
        `).join('');

        return `
            <div class="schema-field card border mb-2 p-3"
                 data-field-id="${createId('field')}">

                <div class="row g-2 align-items-end">

                    <div class="col-md-5">
                        <label class="form-label small">
                            Question label
                        </label>

                        <input
                            type="text"
                            class="form-control field-label"
                            value="${escapeHtml(field.label)}"
                            placeholder="e.g. Participant name"
                            maxlength="255"
                            required
                        >
                    </div>

                    <div class="col-md-3">
                        <label class="form-label small">
                            Answer type
                        </label>

                        <select class="form-select field-type">
                            ${options}
                        </select>
                    </div>

                    <div class="col-md-2">
                        <div class="form-check pb-2">
                            <input
                                class="form-check-input field-required"
                                type="checkbox"
                                ${field.required ? 'checked' : ''}
                            >

                            <label class="form-check-label small">
                                Required
                            </label>
                        </div>
                    </div>

                    <div class="col-md-2">
                        <button
                            type="button"
                            class="btn btn-outline-danger w-100 remove-field"
                            aria-label="Remove question"
                        >
                            <i class="bi bi-trash"></i>
                            Remove
                        </button>
                    </div>

                    <div class="col-12 choices-wrap"
                         style="display: ${type === 'select' ? 'block' : 'none'}">

                        <label class="form-label small">
                            Dropdown choices
                            <span class="text-muted">
                                (separate with commas)
                            </span>
                        </label>

                        <input
                            type="text"
                            class="form-control field-choices"
                            value="${escapeHtml(choices)}"
                            placeholder="Yes, No, Not applicable"
                        >

                        <div class="form-text">
                            Enter each available answer separated by a comma.
                        </div>
                    </div>

                    <div class="col-md-6 linked-record-wrap"
                         style="display: ${type === 'linked_record' ? 'block' : 'none'}">
                        <label class="form-label small">Linked record source</label>
                        <select class="form-select field-linked-model">
                            ${LINKED_SOURCES.map(source => `<option value="${source[0]}" ${linkedModel === source[0] ? 'selected' : ''}>${source[1]}</option>`).join('')}
                        </select>
                        <div class="form-text">Choices are populated from saved attendance records.</div>
                    </div>

                </div>
            </div>
        `;
    }


    /* ==============================================================
       5. SECTION TEMPLATE
       ============================================================== */

    function sectionTemplate(section = {}) {
        const fields = Array.isArray(section.fields) &&
            section.fields.length
            ? section.fields
            : [{ ...DEFAULT_FIELD }];

        const fieldHtml = fields
            .map(field => fieldTemplate(field))
            .join('');

        return `
            <div class="schema-builder-section panel border mb-3 p-3"
                 data-section-id="${createId('section')}">

                <div class="row g-2 align-items-end">

                    <div class="col-md-7">
                        <label class="form-label">
                            Section title
                        </label>

                        <input
                            type="text"
                            class="form-control section-title"
                            value="${escapeHtml(section.title)}"
                            placeholder="e.g. Participant details"
                            maxlength="255"
                            required
                        >
                    </div>

                    <div class="col-md-3">
                        <div class="form-check pb-2">
                            <input
                                class="form-check-input section-repeatable"
                                type="checkbox"
                                ${section.repeatable ? 'checked' : ''}
                            >

                            <label class="form-check-label">
                                Repeatable section
                            </label>
                        </div>
                    </div>

                    <div class="col-md-2">
                        <button
                            type="button"
                            class="btn btn-outline-danger w-100 remove-section"
                            aria-label="Remove section"
                        >
                            <i class="bi bi-trash"></i>
                            Remove
                        </button>
                    </div>

                </div>

                <div class="fields-list mt-3">
                    ${fieldHtml}
                </div>

                <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mt-2">

                    <button
                        type="button"
                        class="btn btn-sm btn-outline-primary add-field"
                    >
                        <i class="bi bi-plus-circle"></i>
                        Add question
                    </button>

                    <span class="text-muted small field-count">
                        ${fields.length} question${fields.length === 1 ? '' : 's'}
                    </span>

                </div>

            </div>
        `;
    }


    /* ==============================================================
       6. SECTION MANAGEMENT
       ============================================================== */

    function updateEmptyState() {
        if (!emptyState) return;

        const hasSections = builder.querySelector(
            '.schema-builder-section'
        );

        emptyState.style.display = hasSections ? 'none' : 'block';
    }

    function addSection(section = {}) {
        builder.insertAdjacentHTML(
            'beforeend',
            sectionTemplate({
                ...DEFAULT_SECTION,
                ...section
            })
        );

        updateEmptyState();
    }

    function addNewSection() {
        addSection();
        syncSchema();

        const sections = builder.querySelectorAll(
            '.schema-builder-section'
        );

        sections[sections.length - 1]
            ?.querySelector('.section-title')
            ?.focus();
    }

    function removeSection(element) {
        const section = element.closest(
            '.schema-builder-section'
        );

        if (!section) return;

        section.remove();

        updateEmptyState();
        syncSchema();
    }


    /* ==============================================================
       7. FIELD MANAGEMENT
       ============================================================== */

    function addField(button) {
        const section = button.closest(
            '.schema-builder-section'
        );

        if (!section) return;

        const fieldsList = section.querySelector('.fields-list');

        fieldsList.insertAdjacentHTML(
            'beforeend',
            fieldTemplate({ ...DEFAULT_FIELD })
        );

        updateFieldCount(section);
        syncSchema();

        fieldsList.querySelector(
            '.schema-field:last-child .field-label'
        )?.focus();
    }

    function removeField(button) {
        const field = button.closest('.schema-field');

        if (!field) return;

        const section = field.closest(
            '.schema-builder-section'
        );

        const fieldsList = section?.querySelector('.fields-list');

        // Every section must contain at least one question.
        if (fieldsList?.querySelectorAll('.schema-field').length <= 1) {
            alert('Each section must contain at least one question.');
            return;
        }

        field.remove();

        updateFieldCount(section);
        syncSchema();
    }

    function updateFieldCount(section) {
        if (!section) return;

        const count = section.querySelectorAll(
            '.schema-field'
        ).length;

        const counter = section.querySelector('.field-count');

        if (counter) {
            counter.textContent =
                `${count} question${count === 1 ? '' : 's'}`;
        }
    }


    /* ==============================================================
       8. SCHEMA COLLECTION
       ============================================================== */

    function collectSchema() {
        return [...builder.querySelectorAll(
            '.schema-builder-section'
        )].map((section, sectionIndex) => {

            const fields = [
                ...section.querySelectorAll('.schema-field')
            ].map((field, fieldIndex) => {

                const type = getFieldType(
                    field.querySelector('.field-type').value
                );

                const label = field.querySelector(
                    '.field-label'
                ).value.trim();

                const choices = type === 'select'
                    ? parseChoices(
                        field.querySelector('.field-choices').value
                    )
                    : [];

                return {
                    name: `field_${fieldIndex + 1}`,
                    label,
                    type,
                    required: field.querySelector(
                        '.field-required'
                    ).checked,
                    choices,
                    linked_model: field.querySelector('.field-linked-model')?.value || ''
                };
            });

            return {
                title: section.querySelector(
                    '.section-title'
                ).value.trim(),

                key: `section_${sectionIndex + 1}`,

                repeatable: section.querySelector(
                    '.section-repeatable'
                ).checked,

                fields
            };
        });
    }


    /* ==============================================================
       9. SCHEMA VALIDATION
       ============================================================== */

    function validateSchema(schema) {
        const errors = [];

        if (!schema.length) {
            errors.push('Add at least one form section.');
        }

        schema.forEach((section, sectionIndex) => {

            if (!section.title) {
                errors.push(
                    `Section ${sectionIndex + 1}: Enter a section title.`
                );
            }

            if (!section.fields.length) {
                errors.push(
                    `${section.title}: Add at least one question.`
                );
            }

            section.fields.forEach((field, fieldIndex) => {

                const location =
                    `${section.title || `Section ${sectionIndex + 1}`}, ` +
                    `question ${fieldIndex + 1}`;

                if (!field.label) {
                    errors.push(
                        `${location}: Enter a question label.`
                    );
                }

                if (
                    field.type === 'select' &&
                    field.choices.length === 0
                ) {
                    errors.push(
                        `${location}: Provide at least one dropdown choice.`
                    );
                }

                if (
                    field.type === 'select' &&
                    new Set(field.choices).size !== field.choices.length
                ) {
                    errors.push(
                        `${location}: Remove duplicate dropdown choices.`
                    );
                }
            });
        });

        return errors;
    }


    /* ==============================================================
       10. SYNCHRONIZE WITH DJANGO
       ============================================================== */

    function syncSchema() {
        const schema = collectSchema();

        hiddenSchema.value = JSON.stringify(schema);

        return schema;
    }


    /* ==============================================================
       11. EVENT LISTENERS
       ============================================================== */

    if (buttons.addTop) {
        buttons.addTop.addEventListener(
            'click',
            addNewSection
        );
    }

    if (buttons.addBottom) {
        buttons.addBottom.addEventListener(
            'click',
            addNewSection
        );
    }

    if (buttons.addFirst) {
        buttons.addFirst.addEventListener(
            'click',
            addNewSection
        );
    }


    // Delegated click events for dynamic controls.
    builder.addEventListener('click', event => {

        const target = event.target.closest('button');

        if (!target) return;

        if (target.classList.contains('remove-section')) {
            removeSection(target);
            return;
        }

        if (target.classList.contains('add-field')) {
            addField(target);
            return;
        }

        if (target.classList.contains('remove-field')) {
            removeField(target);
        }
    });


    // Dropdown visibility and schema synchronization.
    builder.addEventListener('change', event => {

        const target = event.target;

        if (target.classList.contains('field-type')) {

            const field = target.closest('.schema-field');

            const choicesWrap = field.querySelector(
                '.choices-wrap'
            );

            choicesWrap.style.display =
                target.value === 'select' ? 'block' : 'none';

            field.querySelector('.linked-record-wrap').style.display =
                target.value === 'linked_record' ? 'block' : 'none';

            if (target.value !== 'select') {
                field.querySelector(
                    '.field-choices'
                ).value = '';
            }
        }

        syncSchema();
    });


    // Synchronize text inputs and other field changes.
    builder.addEventListener('input', () => {
        syncSchema();
    });


    // Validate before Django form submission.
    definitionForm.addEventListener('submit', event => {

        const schema = syncSchema();
        const errors = validateSchema(schema);

        if (errors.length) {
            event.preventDefault();

            alert(
                'Please correct the following form errors:\n\n' +
                errors.map((error, index) =>
                    `${index + 1}. ${error}`
                ).join('\n')
            );

            return;
        }

    });


    /* ==============================================================
       12. INITIALIZE EXISTING SCHEMA
       ============================================================== */

    const initialSchema = parseInitialSchema();

    initialSchema.forEach(section => {
        addSection(section);
    });

    updateEmptyState();

    syncSchema();

});
