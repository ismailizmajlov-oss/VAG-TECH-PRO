# Official Russian OTTS register access and permission route — 2026-11-08

## Decision

The official Russian vehicle-approval registry is a real primary source, but the current public evidence does not establish a reusable bulk-data licence for VAG TECH PRO.

The official FGIS description says that the registry is used to maintain Russian OTTS/OTSH records, cancellation notices and the national part of the EAEU vehicle-approval register. It also describes data collection from accredited certification bodies and testing laboratories.

The official Interstandart FAQ states that the special software package named «Макет реестра ОТТС/ОТШ ТС» is provided only where the applicant's Rosakkreditatsiya accreditation record includes work under TR TS 018/2011 or GOST 33670. VAG TECH PRO is not an accredited certification body or testing laboratory. The project must not apply for that restricted software or represent itself as an eligible accredited organization.

This is a restriction on that software-delivery workflow. It is **not** interpreted as proof that every public registry record is confidential or that ordinary public lookup is prohibited. Equally, public visibility and export controls do not establish a right to bulk extract, persistently cache, display offline, redistribute, or create a substantial derivative database.

No source rights have been upgraded. No registry account, software, API, export, paid service, document or record was requested or downloaded. No data were imported and no source snapshot SHA-256 is claimed.

## Primary-source observations

### FGIS registry scope

The official FGIS description identifies these functions and document classes:

- Russian national OTTS and OTSH registers;
- notices cancelling OTTS and OTSH;
- the national part of the unified EAEU OTTS/OTSH/SBKTS and cancellation-notice register;
- collection of issued-document information from certification bodies and testing laboratories.

The page separately describes special software for accredited certification bodies and testing laboratories working under TR TS 018/2011. It does not publish a VAG TECH PRO-compatible public bulk API specification or a dataset-specific reuse licence.

### Special software eligibility

The official Interstandart FAQ describes the request procedure for «Макет реестра ОТТС/ОТШ ТС» and says the applicant must have an accreditation scope covering TR TS 018/2011 or GOST 33670 in its official Rosakkreditatsiya card.

This means that route is not available to VAG TECH PRO as an ordinary software developer. Do not bypass the eligibility requirement, borrow another organization's credentials, or treat access to the software as a data-redistribution licence.

### Public ELPTS page

The previously reviewed public ELPTS OTTS page exposed CSV, PDF and XML controls, but the export endpoint, full export scope, dataset-specific terms, persistent-cache rights, offline display rights and redistribution rights were not established. No export was activated. Those controls remain an access observation only.

### EAEU roadmap

EEC Collegium Order No. 126 of 2026-08-11 sets planned legal/administrative milestones for Q4 2026 and Q1 2027 concerning the unified register and electronic information in national parts. The plan is not itself a live API, data export, completed implementation, or licence. Re-check the actual adopted amendments and technical publication before changing source status.

## Permission request route

The official Interstandart public contact page lists:

- General contact: interst@interstandart.ru
- Telephone: +7 (499) 236 03 70
- Official contacts page: https://www.interstandart.ru/page/contacts
- Official FGIS vehicle-register description: https://www.interstandart.ru/page/fgis_01
- Official FAQ, including special OTTS/OTSH software eligibility: https://interstandart.ru/quest

A request may be sent to the published general contact asking it to route the enquiry to the legal/data-rights owner or FGIS register operator. The contact address is not proof that the recipient owns every underlying dataset or has authority to grant all requested rights.

## Draft written enquiry (not sent)

**Subject:** Request for written terms for licensed reuse of public OTTS/OTSH registry data in an offline technical reference application

Уважаемые коллеги!

Разрабатывается автономное справочно-техническое приложение VAG TECH PRO для Windows 10/11 x64. Проект не является органом по сертификации или испытательной лабораторией и не претендует на получение специального программного обеспечения, предоставляемого аккредитованным организациям.

Просим сообщить, кто является надлежащим владельцем данных и уполномочен предоставить письменное разрешение на использование общедоступных сведений российского реестра ОТТС/ОТШ и национальной части единого реестра ЕАЭС для следующего ограниченного сценария:

1. Получение официально опубликованных записей ОТТС/ОТШ и уведомлений об отмене по документированному публичному или лицензированному интерфейсу, с согласованными объёмом, частотой и техническими лимитами.
2. Сохранение разрешённых полей и копий разрешённых документов в локальной SQLite-базе автономного приложения.
3. Отображение этих сведений конечным пользователям приложения без постоянного подключения к сети.
4. Распространение согласованного набора данных вместе с установщиком и обновлениями приложения либо его загрузка пользователем из согласованного официального источника.
5. Создание поисковых индексов и нормализованных полей при обязательном сохранении исходных значений, номера документа, редакции, статуса, области модификации, ссылки на источник и контрольной суммы исходного файла.
6. Хранение истории редакций, обновление и удаление отозванных или ошибочно опубликованных записей в соответствии с установленными сроками и правилами.

Просим отдельно подтвердить или исключить для каждого вида материалов:

- массовое получение и автоматизированную выгрузку;
- локальное долговременное хранение и offline-кэширование;
- отображение сведений конечным пользователям;
- включение записей и файлов документов в дистрибутивы и обновления;
- коммерческое и некоммерческое использование;
- создание производных поисковых индексов и нормализованных справочников;
- хранение исторических редакций;
- отображение полных заполненных приложений № 1 к ОТТС/ОТШ, включая поля двигателя, ЭБУ, коробки передач, передаточных чисел и точной модификации;
- обязательную атрибуцию, уведомления, ограничения по территории, сроку, аудитам и удалению данных.

Просим предоставить действующие условия/лицензию, перечень разрешённых полей и типов документов, описание официального API или экспорта, порядок получения обновлений, тарифы (если применимо), а также указать юридическое лицо и должностное лицо, уполномоченное подписать разрешение.

До получения однозначного письменного разрешения проект не выполняет массовую выгрузку, не сохраняет записи реестра в продуктовой базе и не распространяет документы или их содержимое.

С уважением,
Команда проекта VAG TECH PRO

## Minimum evidence required before enabling ingestion

A response is not sufficient if it only confirms that a page is publicly viewable or that an export button exists. Before enabling any acquisition or product import, retain:

1. The signed licence, permission letter, or dataset-specific terms, including the legal grantor and evidence of authority.
2. Explicit scope for bulk retrieval, local persistent storage, offline end-user display, installer/update redistribution, and any derived indexes.
3. The exact covered register, document types, fields, attachments, markets, historical range, update cadence and retention/deletion obligations.
4. API/export documentation, authentication requirements, rate limits and technical restrictions.
5. Attribution text, territory, term, fee and termination/change-notice terms.
6. A test sample supplied or explicitly designated for reuse, with original file bytes and SHA-256.
7. Privacy and redaction rules. SBKTS and personal/vehicle-identifying fields remain excluded by default.
8. A separate technical-review plan. An Annex 1 raw manufacturer make/type string must not be silently mapped to a VAG three-letter engine or gearbox code.

Only after these checks may the source register be updated. Rights approval alone does not establish technical applicability: exact model/generation/year/variant and engine/gearbox/ECU claims still require document-level evidence and independent technical review.

## Project state

- Source status: permission required / discovery only.
- `data_ingested=false`.
- `product_import_allowed=false`.
- No snapshot exists; SHA-256 is intentionally null.
- No special software, external account, paid plan or third-party credentials were used.
- No contact was sent. This document is a prepared route for a future owner-authorized enquiry.
