Hallöchen. Ich hab Query Device Details gefunden

{
"result": {
"active_time": 1746931457,
"bind_space_id": "170019991",
"category": "yyj",
"create_time": 1743302680,
"custom_name": "",
"icon": "smart/icon/bay1630937774182zJvi/14b212d5befb310bafb1f2b8dbfb7df9.png",
"id": "bf34515c4ab6ecYYYYYY",
"ip": "redacted",
"is_online": true,
"lat": "50.41",
"local_key": "redacted",
"lon": "7.27",
"model": "SOLO HCM",
"name": "KKT Kolbe SOLO HCM",
"product_id": "bgvbvjwomgbisd8x",
"product_name": "KKT Kolbe SOLO HCM",
"sub": false,
"time_zone": "+02:00",
"update_time": 1746931459,
"uuid": "redacted"
},
"success": true,
"t": 1765473690226,
"tid": "d51ae150d6b511f0907cf2f713bbc069"
}

Wenn das nicht das richtige ist brauche ich bitte genauere
Anweisungen. Ich bin unter Device Management und dann wie gesagt Query
Device Details gegangen.


Query Device Details in Bulk wäre das hier




{
"result": [
{
"active_time": 1746931457,
"bind_space_id": "170019991",
"category": "yyj",
"create_time": 1743302680,
"custom_name": "",
"icon": "smart/icon/bay1630937774182zJvi/14b212d5befb310bafb1f2b8dbfb7df9.png",
"id": "bf34515c4ab6ecXXXXXX",
"ip": "redacted",
"is_online": true,
"lat": "50.41",
"local_key": "redacted",
"lon": "7.27",
"model": "SOLO HCM",
"name": "KKT Kolbe SOLO HCM",
"product_id": "bgvbvjwomgbisd8x",
"product_name": "KKT Kolbe SOLO HCM",
"sub": false,
"time_zone": "+02:00",
"update_time": 1746931459,
"uuid": "redacted"
}
],
"success": true,
"t": 1765473853546,
"tid": "3678d8b5d6b611f0bfd7de116888fc39"
}

Device State ist das hier

{
"code": 1108,
"msg": "uri path invalid",
"success": false,
"t": 1765473887911,
"tid": "4aff34d7d6b611f0907cf2f713bbc069"
}

Get instruction set of device

{
"result": {
"category": "yyj",
"functions": [
{
"code": "switch",
"desc": "switch",
"name": "switch",
"type": "Boolean",
"values": "{}"
},
{
"code": "light",
"desc": "light",
"name": "light",
"type": "Boolean",
"values": "{}"
},
{
"code": "switch_lamp",
"desc": "switch lamp",
"name": "switch lamp",
"type": "Boolean",
"values": "{}"
},
{
"code": "switch_wash",
"desc": "switch wash",
"name": "switch wash",
"type": "Boolean",
"values": "{}"
}
]
},
"success": true,
"t": 1765474017323,
"tid": "981899edd6b611f091dbb67f4af8076d"
}

Get the specifications and properties of the device

{
"result": {
"category": "yyj",
"functions": [
{
"code": "switch",
"desc": "{}",
"name": "开关",
"type": "Boolean",
"values": "{}"
},
{
"code": "light",
"desc": "{}",
"name": "灯光",
"type": "Boolean",
"values": "{}"
},
{
"code": "switch_lamp",
"desc": "{}",
"name": "灯带开关",
"type": "Boolean",
"values": "{}"
},
{
"code": "switch_wash",
"desc": "{}",
"name": "清洗开关",
"type": "Boolean",
"values": "{}"
}
],
"status": [
{
"code": "switch",
"name": "开关",
"type": "Boolean",
"values": "{}"
},
{
"code": "light",
"name": "灯光",
"type": "Boolean",
"values": "{}"
},
{
"code": "switch_lamp",
"name": "灯带开关",
"type": "Boolean",
"values": "{}"
},
{
"code": "switch_wash",
"name": "清洗开关",
"type": "Boolean",
"values": "{}"
}
]
},
"success": true,
"t": 1765474048490,
"tid": "aab01426d6b611f091dbb67f4af8076d"
}

Get the instruction set of the catagory

{
"result": {
"category": "bf34515c4ab6ecXXXXXX",
"functions": []
},
"success": true,
"t": 1765474108925,
"tid": "ceb0fa9fd6b611f0907cf2f713bbc069"
}

Ich hoffe du kannst mit irgendwas etwas anfangen :)


Vielen lieben Dank schon mal für deine Mühe

