# Owner-prepared request: Russian FGIS / EAEU OTTS metadata and reuse rights

Status: **draft only — not sent**  
Prepared: 2026-11-09  
Project: VAG TECH PRO, offline Windows 10/11 x64 application

This document is a request template for the project owner. It does not create an account, request paid software, accept a contract, or authorize access to a restricted system. The project has not contacted the authority on the owner's behalf.

## Why this route is being requested

EEC Collegium Decision No. 225 of 2014-12-02 provides that the unified vehicle-approval register consists of national parts, that the relevant fields are published on official websites within five working days, and that authorized bodies provide information from national parts on requests from interested persons (paragraphs 2–5, 8–11 and 13). This establishes a public-information/request route; it does **not** by itself grant VAG TECH PRO rights for bulk reuse, persistent offline caching, third-party display, or redistribution.

The Russian national-part route linked from the official ELPTS site is:

- https://www.rst.gov.ru/portal/gost/home/activity/compliance/evaluationcompliance/AcknowledgementCorrespondence

The FGIS operator's official source page identifies the vehicle conformity-register system:

- https://www.interstandart.ru/page/fgis_01

The operator's official FAQ describes a separate software package ("Макет реестра ОТТС/ОТШ") and states that access to that software requires an accreditation scope containing TR TS 018/2011 or GOST 33670, as well as IBM/HCL Domino. **This request is not an application for that software or for a Domino licence.** The FAQ's software eligibility rules must not be mistaken for the legal basis for an information request under Decision No. 225.

## Verified public contact route

The official Interstandart contacts page lists:

- Email: interst@interstandart.ru
- IT department email: 2364383@interstandart.ru
- Telephone: +7 (499) 236 03 70
- Address: 119049, Moscow, Leninsky Prospekt, 9

Official contact page: https://www.interstandart.ru/page/contacts  
Official FGIS FAQ: https://www.interstandart.ru/quest

Before sending, the owner should verify that these contacts and the responsible authority are still current. If Interstandart is not the competent recipient for a particular request, ask it to identify the authorized body responsible for the Russian national part.

## Draft letter (Russian)

**Кому:** ФБУ «КВФ „Интерстандарт“» / уполномоченному органу, ведущему российскую национальную часть единого реестра  
**Тема:** Запрос сведений и условий повторного использования метаданных ОТТС для справочного приложения VAG TECH PRO

Уважаемые коллеги!

Просим рассмотреть настоящий запрос как запрос заинтересованного лица о предоставлении сведений из российской национальной части единого реестра в соответствии с пунктом 13 Положения, утверждённого Решением Коллегии Евразийской экономической комиссии от 02.12.2014 № 225.

Мы разрабатываем VAG TECH PRO — автономное справочно-диагностическое приложение для Windows 10/11 x64. В текущей модели распространения приложение планируется предоставлять пользователям без оплаты. Приложение не является системой сертификации, не выдаёт заключений о соответствии и не заменяет официальную проверку документа.

Просим сообщить:

1. Какой орган является владельцем сведений и уполномоченным органом по предоставлению данных российской национальной части реестра ОТТС/ОТШ, и кто вправе согласовать условия их повторного использования.
2. Какой официальный публичный маршрут и какая действующая редакция схемы/словаря полей применяются к электронно оформленным ОТТС, включая сведения о статусе, приостановлении, возобновлении, продлении и прекращении действия документа.
3. Возможно ли предоставить машиночитаемую выборку **только по документам ОТТС** для изготовителей/марок Volkswagen, Audi, Škoda, SEAT и CUPRA, либо сообщить официальный порядок получения таких сведений по отдельным документам. Предпочтительные форматы: JSON, XML или CSV; при отсутствии машинного формата просим сообщить доступный официальный формат.
4. Для каждой записи просим, если эти сведения входят в разрешённый к предоставлению состав: регистрационный номер и вид документа, редакцию/дополнение, дату оформления, начало и окончание срока действия, текущий статус и даты изменения статуса, марку, коммерческое наименование, тип, базовое ТС/шасси, модификации, категорию, экологический класс, изготовителя и ссылку на официальную карточку/печатную форму.
5. Существуют ли официальные технические поля или приложения, позволяющие установить обозначение двигателя и трансмиссии для конкретного типа/варианта/версии. Если да, просим указать их точные названия, область доступности и допустимый способ получения. Мы не будем трактовать поле «марка/тип двигателя» как заводской код двигателя, поле трансмиссии — как код КПП, или выводить пару двигатель–КПП без явной привязки к одному и тому же варианту/версии.
6. Предусмотрены ли официальные машинно-читаемые выгрузки и обновления/дельты, каковы их периодичность, версия, контрольные суммы и правила корректного указания редакции документа.

Отдельно просим письменно разъяснить правовые условия использования предоставленных сведений в VAG TECH PRO. Для принятия данных в локальную SQLite нам необходимо получить однозначный ответ, разрешены ли:

- получение и обработка согласованной массовой выборки (или иной согласованный объём);
- сохранение разрешённых полей в локальной SQLite и постоянное offline-кэширование;
- отображение этих полей конечным пользователям бесплатного Windows-приложения;
- включение согласованной выборки в установщик и последующие обновления приложения;
- обновление и хранение предыдущих редакций записей для аудита;
- нормализация названий и связывание записи с внутренним идентификатором документа без изменения исходного значения;
- использование сведений в коммерческом продукте, если такое использование допускается отдельно.

Просим указать точный правовой акт, лицензию или выдать письменное разрешение, в котором перечислены разрешённые поля, цели использования, рынки, срок действия, требования к атрибуции, ограничения на перераспространение, правила обновления и условия прекращения/удаления данных. Если коммерческое использование не допускается, просим прямо указать это; мы не будем считать разрешение на бесплатное использование разрешением на коммерческое использование.

Для минимизации обработки персональных данных просим не включать в выборку сведения о физических лицах, контактные данные заявителей/представителей, VIN отдельных транспортных средств, подписи и иные персональные данные. Свидетельства о безопасности конструкции транспортного средства (СБКТС) в настоящий запрос не включаются.

До получения однозначного разрешения мы не будем выполнять автоматизированную массовую выгрузку, сохранять записи в производственной базе, распространять документы или использовать закрытое программное обеспечение реестра.

Заранее благодарим за разъяснение порядка получения сведений и условий их правомерного повторного использования.

С уважением,  
[ФИО / наименование заявителя]  
[Статус заявителя]  
[Почтовый адрес]  
[Электронная почта и телефон]

## Data-minimisation and scope rules

- Request OTTS metadata first. Keep OTSH as a separate document type if later needed.
- Exclude SBKTS, VIN lists, applicant contact details, personal names and signatures from any proposed product dataset.
- Do not request or store the operator's proprietary software, Domino licence, credentials, browser session, or restricted FGIS access.
- Do not infer engine/gearbox codes from public Annex 2 metadata. The public Annex 2 search fields and the internal FGIS Annex 1 attributes are separate namespaces.
- Do not treat an approval issue date as a vehicle model year.
- A record can support document-level/type-approval scope only. Exact VAG vehicle, generation, year, engine, gearbox, ECU or repair applicability requires primary evidence at the corresponding precision.

## Owner checklist before sending

- [ ] Confirm the applicant identity and authority to make the request.
- [ ] Confirm that the intended release remains no-charge, or explicitly describe any commercial use being requested.
- [ ] Review the current official contacts and legal text.
- [ ] Attach no customer VINs, personal data, passwords, API keys or third-party documents.
- [ ] Do not accept a paid offer, subscription, software licence or contract as part of this request.
- [ ] Do not send until the owner approves the final letter.

## Import gate after a reply

A reply that merely confirms public search, public visibility, or the right to receive an individual record is insufficient for bulk import. Before any import, the owner must review written terms covering the exact source, fields, scope and Windows distribution model. The existing importer also requires a matching permission/licence evidence file and SHA-256, but a matching hash proves file integrity only—not the authenticity or legal sufficiency of the permission.

Even after rights clearance, imported rows must remain document-level candidates until independently reviewed. Engine/gearbox pair promotion requires canonical factory codes explicitly tied to the same exact approval variant and supporting primary evidence. No OTTS metadata can establish DTC, ECU, wiring, pinout, torque, adaptation or repair-procedure applicability by itself.

## Sources reviewed

- EEC Decision No. 225 record in the official EAEU legal portal: https://docs.eaeunion.org/documents/446/10066?PAGEN_1=84
- Decision No. 225 text (secondary legal reproduction used for paragraph-level review): https://www.alta.ru/tamdoc/14kr0225/
- Official Interstandart FGIS page: https://www.interstandart.ru/page/fgis_01
- Official Interstandart FAQ: https://www.interstandart.ru/quest
- Official Interstandart contacts: https://www.interstandart.ru/page/contacts
- Official ELPTS-linked Russian national-register route: https://www.rst.gov.ru/portal/gost/home/activity/compliance/evaluationcompliance/AcknowledgementCorrespondence

Review date: 2026-11-09.
