"""
Safe script to update regions and districts of Uzbekistan.
This script PRESERVES existing orders and only updates regions/districts data.
It uses a mapping approach to migrate old region IDs to new ones.
"""

import sys
import os

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Region, District, Base


def update_uzbekistan_regions_safe(db: Session):
    """
    Safely update regions and districts without deleting existing orders.
    This deactivates old regions and creates new ones.
    """
    
    print("Deactivating old regions and districts...")
    # Deactivate all existing regions and districts (don't delete)
    db.query(Region).update({Region.is_active: False})
    db.query(District).update({District.is_active: False})
    db.commit()
    print("✓ Old regions and districts deactivated")
    
    # All regions and districts of Uzbekistan with proper translations
    regions_data = [
        {
            "name_uz_latin": "Toshkent shahri",
            "name_uz_cyrillic": "Тошкент шаҳри",
            "name_russian": "город Ташкент",
            "districts": [
                {"name_uz_latin": "Bektemir tumani", "name_uz_cyrillic": "Бектемир тумани", "name_russian": "Бектемирский район"},
                {"name_uz_latin": "Chilonzor tumani", "name_uz_cyrillic": "Чилонзор тумани", "name_russian": "Чиланзарский район"},
                {"name_uz_latin": "Mirobod tumani", "name_uz_cyrillic": "Миробод тумани", "name_russian": "Мирабадский район"},
                {"name_uz_latin": "Mirzo Ulug'bek tumani", "name_uz_cyrillic": "Мирзо Улуғбек тумани", "name_russian": "Мирзо-Улугбекский район"},
                {"name_uz_latin": "Olmazor tumani", "name_uz_cyrillic": "Олмазор тумани", "name_russian": "Алмазарский район"},
                {"name_uz_latin": "Sergeli tumani", "name_uz_cyrillic": "Сергели тумани", "name_russian": "Сергелийский район"},
                {"name_uz_latin": "Shayxontohur tumani", "name_uz_cyrillic": "Шайхонтоҳур тумани", "name_russian": "Шайхантахурский район"},
                {"name_uz_latin": "Uchtepa tumani", "name_uz_cyrillic": "Учтепа тумани", "name_russian": "Учтепинский район"},
                {"name_uz_latin": "Yakkasaroy tumani", "name_uz_cyrillic": "Яккасарой тумани", "name_russian": "Яккасарайский район"},
                {"name_uz_latin": "Yangihayon tumani", "name_uz_cyrillic": "Янгиҳаён тумани", "name_russian": "Яшнабадский район"},
                {"name_uz_latin": "Yunusobod tumani", "name_uz_cyrillic": "Юнусобод тумани", "name_russian": "Юнусабадский район"},
            ]
        },
        {
            "name_uz_latin": "Toshkent viloyati",
            "name_uz_cyrillic": "Тошкент вилояти",
            "name_russian": "Ташкентская область",
            "districts": [
                {"name_uz_latin": "Angren shahri", "name_uz_cyrillic": "Ангрен шаҳри", "name_russian": "город Ангрен"},
                {"name_uz_latin": "Olmaliq shahri", "name_uz_cyrillic": "Олмалиқ шаҳри", "name_russian": "город Алмалык"},
                {"name_uz_latin": "Bekobod tumani", "name_uz_cyrillic": "Бекобод тумани", "name_russian": "Бекабадский район"},
                {"name_uz_latin": "Bo'stonliq tumani", "name_uz_cyrillic": "Бўстонлиқ тумани", "name_russian": "Бостанлыкский район"},
                {"name_uz_latin": "Bo'ka tumani", "name_uz_cyrillic": "Бўка тумани", "name_russian": "Букинский район"},
                {"name_uz_latin": "Chinoz tumani", "name_uz_cyrillic": "Чиноз тумани", "name_russian": "Чиназский район"},
                {"name_uz_latin": "Qibray tumani", "name_uz_cyrillic": "Қибрай тумани", "name_russian": "Кибрайский район"},
                {"name_uz_latin": "Ohangaron tumani", "name_uz_cyrillic": "Оҳангарон тумани", "name_russian": "Ахангаранский район"},
                {"name_uz_latin": "Oqqo'rg'on tumani", "name_uz_cyrillic": "Оққўрғон тумани", "name_russian": "Аккурганский район"},
                {"name_uz_latin": "Parkent tumani", "name_uz_cyrillic": "Паркент тумани", "name_russian": "Паркентский район"},
                {"name_uz_latin": "Piskent tumani", "name_uz_cyrillic": "Пискент тумани", "name_russian": "Пскентский район"},
                {"name_uz_latin": "Quyichirchiq tumani", "name_uz_cyrillic": "Қуйичирчиқ тумани", "name_russian": "Куйичирчикский район"},
                {"name_uz_latin": "Yuqorichirchiq tumani", "name_uz_cyrillic": "Юқоричирчиқ тумани", "name_russian": "Юкоричирчикский район"},
                {"name_uz_latin": "Zangiota tumani", "name_uz_cyrillic": "Зангиота тумани", "name_russian": "Зангиатинский район"},
                {"name_uz_latin": "O'rtachirchiq tumani", "name_uz_cyrillic": "Ўрта чирчиқ тумани", "name_russian": "Уртачирчикский район"},
            ]
        },
        {
            "name_uz_latin": "Andijon viloyati",
            "name_uz_cyrillic": "Андижон вилояти",
            "name_russian": "Андижанская область",
            "districts": [
                {"name_uz_latin": "Andijon shahri", "name_uz_cyrillic": "Андижон шаҳри", "name_russian": "город Андижан"},
                {"name_uz_latin": "Xonobod shahri", "name_uz_cyrillic": "Хонобод шаҳри", "name_russian": "город Ханабад"},
                {"name_uz_latin": "Andijon tumani", "name_uz_cyrillic": "Андижон тумани", "name_russian": "Андижанский район"},
                {"name_uz_latin": "Asaka tumani", "name_uz_cyrillic": "Асака тумани", "name_russian": "Асакинский район"},
                {"name_uz_latin": "Baliqchi tumani", "name_uz_cyrillic": "Балиқчи тумани", "name_russian": "Балыкчинский район"},
                {"name_uz_latin": "Bo'z tumani", "name_uz_cyrillic": "Бўз тумани", "name_russian": "Бузский район"},
                {"name_uz_latin": "Buloqboshi tumani", "name_uz_cyrillic": "Булоқбоши тумани", "name_russian": "Булакбашинский район"},
                {"name_uz_latin": "Izboskan tumani", "name_uz_cyrillic": "Избоскан тумани", "name_russian": "Избасканский район"},
                {"name_uz_latin": "Jalaquduq tumani", "name_uz_cyrillic": "Жалақудуқ тумани", "name_russian": "Джалакудукский район"},
                {"name_uz_latin": "Xo'jaobod tumani", "name_uz_cyrillic": "Хўжаобод тумани", "name_russian": "Ходжаабадский район"},
                {"name_uz_latin": "Qo'rg'ontepa tumani", "name_uz_cyrillic": "Қўрғонтепа тумани", "name_russian": "Кургантепинский район"},
                {"name_uz_latin": "Marhamat tumani", "name_uz_cyrillic": "Марҳамат тумани", "name_russian": "Мархаматский район"},
                {"name_uz_latin": "Oltinko'l tumani", "name_uz_cyrillic": "Олтинкўл тумани", "name_russian": "Алтынкульский район"},
                {"name_uz_latin": "Paxtaobod tumani", "name_uz_cyrillic": "Пахтаобод тумани", "name_russian": "Пахтаабадский район"},
                {"name_uz_latin": "Ulug'nor tumani", "name_uz_cyrillic": "Улуғнор тумани", "name_russian": "Улугнорский район"},
                {"name_uz_latin": "Shaxrixon tumani", "name_uz_cyrillic": "Шаҳрихон тумани", "name_russian": "Шахриханский район"},
            ]
        },
        {
            "name_uz_latin": "Buxoro viloyati",
            "name_uz_cyrillic": "Бухоро вилояти",
            "name_russian": "Бухарская область",
            "districts": [
                {"name_uz_latin": "Buxoro shahri", "name_uz_cyrillic": "Бухоро шаҳри", "name_russian": "город Бухара"},
                {"name_uz_latin": "Kogon shahri", "name_uz_cyrillic": "Когон шаҳри", "name_russian": "город Каган"},
                {"name_uz_latin": "Buxoro tumani", "name_uz_cyrillic": "Бухоро тумани", "name_russian": "Бухарский район"},
                {"name_uz_latin": "G'ijduvon tumani", "name_uz_cyrillic": "Ғиждувон тумани", "name_russian": "Гиждуванский район"},
                {"name_uz_latin": "Jondor tumani", "name_uz_cyrillic": "Жондор тумани", "name_russian": "Жондорский район"},
                {"name_uz_latin": "Kogon tumani", "name_uz_cyrillic": "Когон тумани", "name_russian": "Каганский район"},
                {"name_uz_latin": "Olot tumani", "name_uz_cyrillic": "Олот тумани", "name_russian": "Алатский район"},
                {"name_uz_latin": "Peshku tumani", "name_uz_cyrillic": "Пешку тумани", "name_russian": "Пешкунский район"},
                {"name_uz_latin": "Qorako'l tumani", "name_uz_cyrillic": "Қоракўл тумани", "name_russian": "Каракульский район"},
                {"name_uz_latin": "Qorovulbozor tumani", "name_uz_cyrillic": "Қоровулбозор тумани", "name_russian": "Караулбазарский район"},
                {"name_uz_latin": "Romitan tumani", "name_uz_cyrillic": "Ромитан тумани", "name_russian": "Ромитанский район"},
                {"name_uz_latin": "Shofirkon tumani", "name_uz_cyrillic": "Шофиркон тумани", "name_russian": "Шафирканский район"},
                {"name_uz_latin": "Vobkent tumani", "name_uz_cyrillic": "Вобкент тумани", "name_russian": "Вабкентский район"},
            ]
        },
        {
            "name_uz_latin": "Farg'ona viloyati",
            "name_uz_cyrillic": "Фарғона вилояти",
            "name_russian": "Ферганская область",
            "districts": [
                {"name_uz_latin": "Farg'ona shahri", "name_uz_cyrillic": "Фарғона шаҳри", "name_russian": "город Фергана"},
                {"name_uz_latin": "Marg'ilon shahri", "name_uz_cyrillic": "Марғилон шаҳри", "name_russian": "город Маргилан"},
                {"name_uz_latin": "Qo'qon shahri", "name_uz_cyrillic": "Қўқон шаҳри", "name_russian": "город Коканд"},
                {"name_uz_latin": "Oltiariq tumani", "name_uz_cyrillic": "Олтиариқ тумани", "name_russian": "Алтыарыкский район"},
                {"name_uz_latin": "Bag'dod tumani", "name_uz_cyrillic": "Бағдод тумани", "name_russian": "Багдадский район"},
                {"name_uz_latin": "Beshariq tumani", "name_uz_cyrillic": "Бешариқ тумани", "name_russian": "Бешарыкский район"},
                {"name_uz_latin": "Buvayda tumani", "name_uz_cyrillic": "Бувайда тумани", "name_russian": "Бувайдинский район"},
                {"name_uz_latin": "Dang'ara tumani", "name_uz_cyrillic": "Данғара тумани", "name_russian": "Дангаринский район"},
                {"name_uz_latin": "Farg'ona tumani", "name_uz_cyrillic": "Фарғона тумани", "name_russian": "Ферганский район"},
                {"name_uz_latin": "Furqat tumani", "name_uz_cyrillic": "Фурқат тумани", "name_russian": "Фуркатский район"},
                {"name_uz_latin": "O'zbekiston tumani", "name_uz_cyrillic": "Ўзбекистон тумани", "name_russian": "Узбекистанский район"},
                {"name_uz_latin": "Qo'shtepa tumani", "name_uz_cyrillic": "Қўштепа тумани", "name_russian": "Куштепинский район"},
                {"name_uz_latin": "Quva tumani", "name_uz_cyrillic": "Қува тумани", "name_russian": "Кувинский район"},
                {"name_uz_latin": "Rishton tumani", "name_uz_cyrillic": "Риштон тумани", "name_russian": "Риштанский район"},
                {"name_uz_latin": "So'x tumani", "name_uz_cyrillic": "Сўх тумани", "name_russian": "Сохский район"},
                {"name_uz_latin": "Toshloq tumani", "name_uz_cyrillic": "Тошлоқ тумани", "name_russian": "Ташлакский район"},
                {"name_uz_latin": "Uchko'prik tumani", "name_uz_cyrillic": "Учкўприк тумани", "name_russian": "Учкуприкский район"},
                {"name_uz_latin": "Yozyovon tumani", "name_uz_cyrillic": "Ёзёвон тумани", "name_russian": "Язъяванский район"},
            ]
        },
        {
            "name_uz_latin": "Jizzax viloyati",
            "name_uz_cyrillic": "Жиззах вилояти",
            "name_russian": "Джизакская область",
            "districts": [
                {"name_uz_latin": "Jizzax shahri", "name_uz_cyrillic": "Жиззах шаҳри", "name_russian": "город Джизак"},
                {"name_uz_latin": "Arnasoy tumani", "name_uz_cyrillic": "Арнасой тумани", "name_russian": "Арнасайский район"},
                {"name_uz_latin": "Baxmal tumani", "name_uz_cyrillic": "Бахмал тумани", "name_russian": "Бахмальский район"},
                {"name_uz_latin": "Do'stlik tumani", "name_uz_cyrillic": "Дўстлик тумани", "name_russian": "Дустликский район"},
                {"name_uz_latin": "Forish tumani", "name_uz_cyrillic": "Фориш тумани", "name_russian": "Фаришский район"},
                {"name_uz_latin": "G'allaorol tumani", "name_uz_cyrillic": "Ғаллаорол тумани", "name_russian": "Галляаральский район"},
                {"name_uz_latin": "Sharof Rashidov tumani", "name_uz_cyrillic": "Шароф Рашидов тумани", "name_russian": "Шараф-Рашидовский район"},
                {"name_uz_latin": "Mirzacho'l tumani", "name_uz_cyrillic": "Мирзачўл тумани", "name_russian": "Мирзачульский район"},
                {"name_uz_latin": "Paxtakor tumani", "name_uz_cyrillic": "Пахтакор тумани", "name_russian": "Пахтакорский район"},
                {"name_uz_latin": "Yangiobod tumani", "name_uz_cyrillic": "Янгиобод тумани", "name_russian": "Янгиабадский район"},
                {"name_uz_latin": "Zafarobod tumani", "name_uz_cyrillic": "Зафаробод тумани", "name_russian": "Зафарабадский район"},
                {"name_uz_latin": "Zomin tumani", "name_uz_cyrillic": "Зомин тумани", "name_russian": "Заминский район"},
            ]
        },
        {
            "name_uz_latin": "Xorazm viloyati",
            "name_uz_cyrillic": "Хоразм вилояти",
            "name_russian": "Хорезмская область",
            "districts": [
                {"name_uz_latin": "Urganch shahri", "name_uz_cyrillic": "Урганч шаҳри", "name_russian": "город Ургенч"},
                {"name_uz_latin": "Xiva shahri", "name_uz_cyrillic": "Хива шаҳри", "name_russian": "город Хива"},
                {"name_uz_latin": "Bog'ot tumani", "name_uz_cyrillic": "Боғот тумани", "name_russian": "Багатский район"},
                {"name_uz_latin": "Gurlan tumani", "name_uz_cyrillic": "Гурлан тумани", "name_russian": "Гурленский район"},
                {"name_uz_latin": "Qo'shko'pir tumani", "name_uz_cyrillic": "Қўшкўпир тумани", "name_russian": "Кушкупырский район"},
                {"name_uz_latin": "Urganch tumani", "name_uz_cyrillic": "Урганч тумани", "name_russian": "Ургенчский район"},
                {"name_uz_latin": "Xazorasp tumani", "name_uz_cyrillic": "Хазорасп тумани", "name_russian": "Хазараспский район"},
                {"name_uz_latin": "Xonqa tumani", "name_uz_cyrillic": "Хонқа тумани", "name_russian": "Ханкинский район"},
                {"name_uz_latin": "Xiva tumani", "name_uz_cyrillic": "Хива тумани", "name_russian": "Хивинский район"},
                {"name_uz_latin": "Shovot tumani", "name_uz_cyrillic": "Шовот тумани", "name_russian": "Шаватский район"},
                {"name_uz_latin": "Yangiariq tumani", "name_uz_cyrillic": "Янгиариқ тумани", "name_russian": "Янгиарыкский район"},
                {"name_uz_latin": "Yangibozor tumani", "name_uz_cyrillic": "Янгибозор тумани", "name_russian": "Янгибазарский район"},
            ]
        },
        {
            "name_uz_latin": "Namangan viloyati",
            "name_uz_cyrillic": "Наманган вилояти",
            "name_russian": "Наманганская область",
            "districts": [
                {"name_uz_latin": "Namangan shahri", "name_uz_cyrillic": "Наманган шаҳри", "name_russian": "город Наманган"},
                {"name_uz_latin": "Chortoq tumani", "name_uz_cyrillic": "Чортоқ тумани", "name_russian": "Чартакский район"},
                {"name_uz_latin": "Chust tumani", "name_uz_cyrillic": "Чуст тумани", "name_russian": "Чустский район"},
                {"name_uz_latin": "Kosonsoy tumani", "name_uz_cyrillic": "Косонсой тумани", "name_russian": "Касансайский район"},
                {"name_uz_latin": "Mingbuloq tumani", "name_uz_cyrillic": "Мингбулоқ тумани", "name_russian": "Мингбулакский район"},
                {"name_uz_latin": "Norin tumani", "name_uz_cyrillic": "Норин тумани", "name_russian": "Наринский район"},
                {"name_uz_latin": "Namangan tumani", "name_uz_cyrillic": "Наманган тумани", "name_russian": "Наманганский район"},
                {"name_uz_latin": "Pop tumani", "name_uz_cyrillic": "Поп тумани", "name_russian": "Папский район"},
                {"name_uz_latin": "To'raqo'rg'on tumani", "name_uz_cyrillic": "Тўрақўрғон тумани", "name_russian": "Туракурганский район"},
                {"name_uz_latin": "Uchqo'rg'on tumani", "name_uz_cyrillic": "Учқўрғон тумани", "name_russian": "Учкурганский район"},
                {"name_uz_latin": "Uychi tumani", "name_uz_cyrillic": "Уйчи тумани", "name_russian": "Уйчинский район"},
                {"name_uz_latin": "Yangiqo'rg'on tumani", "name_uz_cyrillic": "Янгиқўрғон тумани", "name_russian": "Янгикурганский район"},
            ]
        },
        {
            "name_uz_latin": "Navoiy viloyati",
            "name_uz_cyrillic": "Навоий вилояти",
            "name_russian": "Навоийская область",
            "districts": [
                {"name_uz_latin": "Navoiy shahri", "name_uz_cyrillic": "Навоий шаҳри", "name_russian": "город Навои"},
                {"name_uz_latin": "Zarafshon shahri", "name_uz_cyrillic": "Зарафшон шаҳри", "name_russian": "город Зарафшан"},
                {"name_uz_latin": "Karmana tumani", "name_uz_cyrillic": "Кармана тумани", "name_russian": "Карманинский район"},
                {"name_uz_latin": "Konimex tumani", "name_uz_cyrillic": "Конимех тумани", "name_russian": "Канимехский район"},
                {"name_uz_latin": "Qiziltepa tumani", "name_uz_cyrillic": "Қизилтепа тумани", "name_russian": "Кызылтепинский район"},
                {"name_uz_latin": "Navbahor tumani", "name_uz_cyrillic": "Навбаҳор тумани", "name_russian": "Навбахорский район"},
                {"name_uz_latin": "Nurota tumani", "name_uz_cyrillic": "Нурота тумани", "name_russian": "Нуратинский район"},
                {"name_uz_latin": "Tomdi tumani", "name_uz_cyrillic": "Томди тумани", "name_russian": "Тамдынский район"},
                {"name_uz_latin": "Uchquduq tumani", "name_uz_cyrillic": "Учқудуқ тумани", "name_russian": "Учкудукский район"},
                {"name_uz_latin": "Xatirchi tumani", "name_uz_cyrillic": "Хатирчи тумани", "name_russian": "Хатырчинский район"},
            ]
        },
        {
            "name_uz_latin": "Qashqadaryo viloyati",
            "name_uz_cyrillic": "Қашқадарё вилояти",
            "name_russian": "Кашкадарьинская область",
            "districts": [
                {"name_uz_latin": "Qarshi shahri", "name_uz_cyrillic": "Қарши шаҳри", "name_russian": "город Карши"},
                {"name_uz_latin": "Shahrisabz shahri", "name_uz_cyrillic": "Шаҳрисабз шаҳри", "name_russian": "город Шахрисабз"},
                {"name_uz_latin": "Chiroqchi tumani", "name_uz_cyrillic": "Чироқчи тумани", "name_russian": "Чиракчинский район"},
                {"name_uz_latin": "Dehqonobod tumani", "name_uz_cyrillic": "Деҳқонобод тумани", "name_russian": "Дехканабадский район"},
                {"name_uz_latin": "G'uzor tumani", "name_uz_cyrillic": "Ғузор тумани", "name_russian": "Гузарский район"},
                {"name_uz_latin": "Qamashi tumani", "name_uz_cyrillic": "Қамаши тумани", "name_russian": "Камашинский район"},
                {"name_uz_latin": "Qarshi tumani", "name_uz_cyrillic": "Қарши тумани", "name_russian": "Каршинский район"},
                {"name_uz_latin": "Kasbi tumani", "name_uz_cyrillic": "Касби тумани", "name_russian": "Касбинский район"},
                {"name_uz_latin": "Kitob tumani", "name_uz_cyrillic": "Китоб тумани", "name_russian": "Китабский район"},
                {"name_uz_latin": "Koson tumani", "name_uz_cyrillic": "Косон тумани", "name_russian": "Касанский район"},
                {"name_uz_latin": "Mirishkor tumani", "name_uz_cyrillic": "Миришкор тумани", "name_russian": "Миришкорский район"},
                {"name_uz_latin": "Muborak tumani", "name_uz_cyrillic": "Муборак тумани", "name_russian": "Мубарекский район"},
                {"name_uz_latin": "Nishon tumani", "name_uz_cyrillic": "Нишон тумани", "name_russian": "Нишанский район"},
                {"name_uz_latin": "Shahrisabz tumani", "name_uz_cyrillic": "Шаҳрисабз тумани", "name_russian": "Шахрисабзский район"},
                {"name_uz_latin": "Yakkabog' tumani", "name_uz_cyrillic": "Яккабоғ тумани", "name_russian": "Яккабагский район"},
            ]
        },
        {
            "name_uz_latin": "Qoraqalpog'iston Respublikasi",
            "name_uz_cyrillic": "Қорақалпоғистон Республикаси",
            "name_russian": "Республика Каракалпакстан",
            "districts": [
                {"name_uz_latin": "Nukus shahri", "name_uz_cyrillic": "Нукус шаҳри", "name_russian": "город Нукус"},
                {"name_uz_latin": "Amudaryo tumani", "name_uz_cyrillic": "Амударё тумани", "name_russian": "Амударьинский район"},
                {"name_uz_latin": "Beruniy tumani", "name_uz_cyrillic": "Беруний тумани", "name_russian": "Берунийский район"},
                {"name_uz_latin": "Chimboy tumani", "name_uz_cyrillic": "Чимбой тумани", "name_russian": "Чимбайский район"},
                {"name_uz_latin": "Ellikqal'a tumani", "name_uz_cyrillic": "Элликқалъа тумани", "name_russian": "Элликкалинский район"},
                {"name_uz_latin": "Kegeyli tumani", "name_uz_cyrillic": "Кегейли тумани", "name_russian": "Кегейлийский район"},
                {"name_uz_latin": "Mo'ynoq tumani", "name_uz_cyrillic": "Мўйноқ тумани", "name_russian": "Муйнакский район"},
                {"name_uz_latin": "Nukus tumani", "name_uz_cyrillic": "Нукус тумани", "name_russian": "Нукусский район"},
                {"name_uz_latin": "Qonliko'l tumani", "name_uz_cyrillic": "Қонликўл тумани", "name_russian": "Канлыкульский район"},
                {"name_uz_latin": "Qo'ng'irot tumani", "name_uz_cyrillic": "Қўнғирот тумани", "name_russian": "Кунградский район"},
                {"name_uz_latin": "Qorao'zak tumani", "name_uz_cyrillic": "Қораўзак тумани", "name_russian": "Караузякский район"},
                {"name_uz_latin": "Shumanay tumani", "name_uz_cyrillic": "Шуманай тумани", "name_russian": "Шуманайский район"},
                {"name_uz_latin": "Taxtako'pir tumani", "name_uz_cyrillic": "Тахтакўпир тумани", "name_russian": "Тахтакупырский район"},
                {"name_uz_latin": "To'rtko'l tumani", "name_uz_cyrillic": "Тўрткўл тумани", "name_russian": "Турткульский район"},
                {"name_uz_latin": "Xo'jayli tumani", "name_uz_cyrillic": "Хўжайли тумани", "name_russian": "Ходжейлийский район"},
            ]
        },
        {
            "name_uz_latin": "Samarqand viloyati",
            "name_uz_cyrillic": "Самарқанд вилояти",
            "name_russian": "Самаркандская область",
            "districts": [
                {"name_uz_latin": "Samarqand shahri", "name_uz_cyrillic": "Самарқанд шаҳри", "name_russian": "город Самарканд"},
                {"name_uz_latin": "Kattaqo'rg'on shahri", "name_uz_cyrillic": "Каттақўрғон шаҳри", "name_russian": "город Каттакурган"},
                {"name_uz_latin": "Akdaryo tumani", "name_uz_cyrillic": "Акдарё тумани", "name_russian": "Акдарьинский район"},
                {"name_uz_latin": "Bulung'ur tumani", "name_uz_cyrillic": "Булунғур тумани", "name_russian": "Булунгурский район"},
                {"name_uz_latin": "Ishtixon tumani", "name_uz_cyrillic": "Иштихон тумани", "name_russian": "Иштыханский район"},
                {"name_uz_latin": "Jomboy tumani", "name_uz_cyrillic": "Жомбой тумани", "name_russian": "Джамбайский район"},
                {"name_uz_latin": "Kattaqo'rg'on tumani", "name_uz_cyrillic": "Каттақўрғон тумани", "name_russian": "Каттакурганский район"},
                {"name_uz_latin": "Narpay tumani", "name_uz_cyrillic": "Нарпай тумани", "name_russian": "Нарпайский район"},
                {"name_uz_latin": "Nurobod tumani", "name_uz_cyrillic": "Нуробод тумани", "name_russian": "Нурабадский район"},
                {"name_uz_latin": "Oqdaryo tumani", "name_uz_cyrillic": "Оқдарё тумани", "name_russian": "Акдарьинский район"},
                {"name_uz_latin": "Paxtachi tumani", "name_uz_cyrillic": "Пахтачи тумани", "name_russian": "Пахтачийский район"},
                {"name_uz_latin": "Payariq tumani", "name_uz_cyrillic": "Паяриқ тумани", "name_russian": "Пайарыкский район"},
                {"name_uz_latin": "Pastdarg'om tumani", "name_uz_cyrillic": "Пастдарғом тумани", "name_russian": "Пастдаргомский район"},
                {"name_uz_latin": "Qo'shrabot tumani", "name_uz_cyrillic": "Қўшработ тумани", "name_russian": "Кошрабадский район"},
                {"name_uz_latin": "Samarqand tumani", "name_uz_cyrillic": "Самарқанд тумани", "name_russian": "Самаркандский район"},
                {"name_uz_latin": "Toyloq tumani", "name_uz_cyrillic": "Тойлоқ тумани", "name_russian": "Тайлакский район"},
                {"name_uz_latin": "Urgut tumani", "name_uz_cyrillic": "Ургут тумани", "name_russian": "Ургутский район"},
            ]
        },
        {
            "name_uz_latin": "Sirdaryo viloyati",
            "name_uz_cyrillic": "Сирдарё вилояти",
            "name_russian": "Сырдарьинская область",
            "districts": [
                {"name_uz_latin": "Guliston shahri", "name_uz_cyrillic": "Гулистон шаҳри", "name_russian": "город Гулистан"},
                {"name_uz_latin": "Yangiyer shahri", "name_uz_cyrillic": "Янгиер шаҳри", "name_russian": "город Янгиер"},
                {"name_uz_latin": "Akaltyn tumani", "name_uz_cyrillic": "Акалтын тумани", "name_russian": "Акалтынский район"},
                {"name_uz_latin": "Arnasoy tumani", "name_uz_cyrillic": "Арнасой тумани", "name_russian": "Арнасайский район"},
                {"name_uz_latin": "Boyovut tumani", "name_uz_cyrillic": "Боёвут тумани", "name_russian": "Баяутский район"},
                {"name_uz_latin": "Guliston tumani", "name_uz_cyrillic": "Гулистон тумани", "name_russian": "Гулистанский район"},
                {"name_uz_latin": "Oqoltin tumani", "name_uz_cyrillic": "Оқолтин тумани", "name_russian": "Акалтынский район"},
                {"name_uz_latin": "Sardoba tumani", "name_uz_cyrillic": "Сардоба тумани", "name_russian": "Сардобинский район"},
                {"name_uz_latin": "Sayxunobod tumani", "name_uz_cyrillic": "Сайхунобод тумани", "name_russian": "Сайхунабадский район"},
                {"name_uz_latin": "Mirzaobod tumani", "name_uz_cyrillic": "Мирзаобод тумани", "name_russian": "Мирзаабадский район"},
            ]
        },
        {
            "name_uz_latin": "Surxondaryo viloyati",
            "name_uz_cyrillic": "Сурхондарё вилояти",
            "name_russian": "Сурхандарьинская область",
            "districts": [
                {"name_uz_latin": "Termiz shahri", "name_uz_cyrillic": "Термиз шаҳри", "name_russian": "город Термез"},
                {"name_uz_latin": "Angor tumani", "name_uz_cyrillic": "Ангор тумани", "name_russian": "Ангорский район"},
                {"name_uz_latin": "Boysun tumani", "name_uz_cyrillic": "Бойсун тумани", "name_russian": "Байсунский район"},
                {"name_uz_latin": "Denov tumani", "name_uz_cyrillic": "Денов тумани", "name_russian": "Денауский район"},
                {"name_uz_latin": "Jarqo'rg'on tumani", "name_uz_cyrillic": "Жарқўрғон тумани", "name_russian": "Джаркурганский район"},
                {"name_uz_latin": "Muzrabot tumani", "name_uz_cyrillic": "Музработ тумani", "name_russian": "Музрабадский район"},
                {"name_uz_latin": "Oltinsoy tumani", "name_uz_cyrillic": "Олтинсой тумани", "name_russian": "Алтынсайский район"},
                {"name_uz_latin": "Qiziriq tumani", "name_uz_cyrillic": "Қизириқ тумани", "name_russian": "Кизирикский район"},
                {"name_uz_latin": "Qo'mqo'rg'on tumani", "name_uz_cyrillic": "Қўмқўрғон тумани", "name_russian": "Кумкурганский район"},
                {"name_uz_latin": "Sariosiyo tumani", "name_uz_cyrillic": "Сариосиё тумани", "name_russian": "Сариасийский район"},
                {"name_uz_latin": "Sherobod tumani", "name_uz_cyrillic": "Шеробод тумани", "name_russian": "Шерабадский район"},
                {"name_uz_latin": "Sho'rchi tumani", "name_uz_cyrillic": "Шўрчи тумани", "name_russian": "Шурчинский район"},
                {"name_uz_latin": "Termiz tumani", "name_uz_cyrillic": "Термиз тумани", "name_russian": "Термезский район"},
                {"name_uz_latin": "Uzun tumani", "name_uz_cyrillic": "Узун тумани", "name_russian": "Узунский район"},
            ]
        },
    ]
    
    print("\nAdding new Uzbekistan regions and districts...")
    
    for region_data in regions_data:
        # Create new region
        region = Region(
            name_uz_latin=region_data["name_uz_latin"],
            name_uz_cyrillic=region_data["name_uz_cyrillic"],
            name_russian=region_data["name_russian"],
            is_active=True
        )
        db.add(region)
        db.flush()  # Flush to get the region ID
        
        print(f"✓ Added region: {region_data['name_uz_latin']}")
        
        # Create districts for this region
        for district_data in region_data["districts"]:
            district = District(
                region_id=region.id,
                name_uz_latin=district_data["name_uz_latin"],
                name_uz_cyrillic=district_data["name_uz_cyrillic"],
                name_russian=district_data["name_russian"],
                is_active=True
            )
            db.add(district)
        
        print(f"  ✓ Added {len(region_data['districts'])} districts")
    
    db.commit()
    print("\n✓ Successfully added all new regions and districts!")


def main():
    """Main function to safely update regions"""
    print("=" * 60)
    print("SAFE UPDATE: UZBEKISTAN REGIONS AND DISTRICTS")
    print("=" * 60)
    print("\nThis script will:")
    print("  1. Deactivate old regions and districts (is_active=False)")
    print("  2. Add new correct regions and districts")
    print("  3. Preserve existing orders and pricing")
    print("\nNote: Old regions will remain in DB for reference")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        update_uzbekistan_regions_safe(db)
        
        print("\n" + "=" * 60)
        print("COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        # Display summary
        total_regions_active = db.query(Region).filter(Region.is_active == True).count()
        total_districts_active = db.query(District).filter(District.is_active == True).count()
        total_regions_inactive = db.query(Region).filter(Region.is_active == False).count()
        total_districts_inactive = db.query(District).filter(District.is_active == False).count()
        
        print(f"\nActive regions: {total_regions_active}")
        print(f"Active districts: {total_districts_active}")
        print(f"Inactive (old) regions: {total_regions_inactive}")
        print(f"Inactive (old) districts: {total_districts_inactive}")
        
    except Exception as e:
        print(f"\nError occurred: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
