#!/usr/bin/env python3
from nicegui import ui, app, run
import time
import db
import serial
import json
import threading
import requests
import websocket
import asyncio
import os

db.init()

columns = [
    {'name': 'cluster_id', 'label': 'Номер канала', 'field': 'cluster_id', 'required': True},
    {'name': 'ha_device', 'label': 'Устройство HA', 'field': 'ha_device', 'sortable': True},
    {'name': 'status', 'label': "Статус", 'field': 'status'},
    {'name': 'enabled', 'label': "Активация канала", 'field': 'enabled'}
]

rows = db.get_devices()
ws = websocket.WebSocket()
device_init = False
reboot_state = False
last_msg_id = 1
ser = serial.Serial()
devices = []  # список девайсов с апи ХА
import serial.tools.list_ports

ws.connect("ws://supervisor/core/websocket")


def connect_uart():
    global ser
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        print("{} {} [{}]".format(port, desc, hwid))
    ser_port = None
    for port, desc, hwid in sorted(ports):
        if "JTAG" in desc:
            ser_port = port
            break
    print("Device found at: ", ser_port)
    ser = serial.Serial(ser_port, 115200)
    print("Device init complete")


def ping_ws():
    while True:
        time.sleep(5)
        ws.ping()


def emit_device_state(device_id, state):
    data = {
        "id": get_request_id(),
        "type": "call_service",
        "domain": device_id.split(".")[0],
        "service": state,
        "target": {
            "entity_id": device_id
        }
    }
    print(data)
    ws.send(json.dumps(data))
    print("Emitted signal to device {} with state {}".format(device_id, state))
    response = ws.recv()
    print("emit result: ", response)


def connect_ws():
    global ws
    auth_data = {
        "type": "auth",
        "access_token": os.environ.get('SUPERVISOR_TOKEN')
    }
    print(auth_data)
    response = ws.recv()
    print(f"Received: {response}")
    ws.send(json.dumps(auth_data))
    response = ws.recv()
    print(f"Received: {response}")


def get_request_id():
    global last_msg_id
    q = last_msg_id
    last_msg_id += 1
    return q


def get_devices_ha():
    global devices, ws, table
    subscribe_payload = json.dumps({
        "id": get_request_id(),
        "type": "subscribe_events",
        "event_type": "state_changed"
    })
    ws.send(subscribe_payload)
    response = ws.recv()
    get_devices_payload = json.dumps({
        "id": get_request_id(),
        "type": "get_states"
    })
    ws.send(get_devices_payload)
    devices_response = ws.recv()
    devices = json.loads(devices_response)
    devices_list = {}
    try:
        for i in devices['result']:
            # Пример: добавление идентификатора и имени устройства в список
            try:
                devices_list[i['entity_id']] = "{} [{}]".format(i['attributes']['friendly_name'], i['entity_id'])
            except:
                devices_list[i['entity_id']] = "{} [{}]".format(i['entity_id'], i['entity_id'])
        devices = devices_list
        ha_device.set_options(devices_list)
        ha_device.update()
    except:
        print(f"Ошибка при получении списка устройств: HA вернул ответ\n{devices}")

def getChannels():
    print(rows)
    result = []
    for i in rows:
        if i['enabled']:
            result.append(i['cluster_id'])
    return result


def getSelectedDevices():
    tmp = []
    for i in rows:
        tmp.append(i['ha_device'])
    return tmp


def stateCheck(message):
    global rows, table
    print(message)
    data = json.loads(message.replace("'", '"'))
    device_id = ""
    for index, i in enumerate(rows):
        if i['cluster_id'] == data['cl']:
            device_id = i['ha_device']
            rows[index]['status'] = False if data['st'] == 0 else True
            table.rows[index]['status'] = False if data['st'] == 0 else True
            table.update()
            break
    print("Cluster: {} | state: {}".format(data['cl'], data['st']))
    emit_device_state(device_id, 'turn_off' if data['st'] == 0 else 'turn_on')


def setup(serial):
    global device_init
    print("Sending init command: ", "init {} \r".format(" ".join(str(i) for i in getChannels())))
    ser.write("init {} \r".format(" ".join(str(i) for i in getChannels())).encode('utf-8'))
    device_init = True


def reboot_device(ser):
    global reboot_state
    while True:
        if reboot_state:
            ser.write("rst \r".encode('utf-8'))
            print("Sent rst command")
            reboot_state = False
        time.sleep(0.5)


def background_worker():
    global device_init, reboot_state
    connect_uart()
    threading.Thread(target=reboot_device, args=(ser,), daemon=True).start()
    while True:
        try:
         b = ser.readline()
        except:
            print("Потеряли соединение с ESP, переподключаемся...")
            while True:
                try:
                    connect_uart()
                    print("Подключение восстановлено!")
                    ser.write("rst \r".encode('utf-8'))
                    break
                except:
                    time.sleep(0.5)
            continue
        s1 = b.decode('utf-8').rstrip()  # convert to string
        #print("ESP -> ",s1)
        if "coexist: coexist rom version" in s1:
            print("Found ESP32 init.")
            device_init = False

        if "esp32c6>" in s1 and device_init is False:
            print("Sending channel list to ESP32")
            setup(ser)
        check = s1.split("|")
        if len(check) == 3:
            print("Got state change:", check)
            stateCheck(check[1])
        else:
            print(s1)
        log.push(s1)


def refresh_values():
    global rows
    rows = db.get_devices()


def add_device():
    print("val:", cluster_id.value)
    if ha_device.value == None or cluster_id.value == "" or not cluster_id.value.isdigit() or int(
            cluster_id.value) > 240 or ha_device.value in getSelectedDevices():
        cluster_id.validate()
        ha_device.validate()
        return
    print("pass")
    table.add_rows(
        {'id': int(time.time()), 'cluster_id': cluster_id.value, 'ha_device': ha_device.value, 'enabled': True,
         'status': False, 'create': True}),
    cluster_id.set_value(""),
    ha_device.set_value(None),
    save_btn.set_visibility(True)
    table.update()
    cluster_id.error = None
    ha_device.error = None


def change_activation_state(e):
    global rows, reboot_state
    print(e)
    for index, i in enumerate(rows):
        if i['cluster_id'] == e.args['cluster_id']:
            rows[index]['enabled'] = e.args['enabled']
            table.rows[index]['enabled'] = e.args['enabled']
            break
    print("Change state to ", e.args['cluster_id'], " on state ", e.args['enabled'])
    # reboot_state = True
    save_btn.set_visibility(True)
    table.update()
    print(rows)


def save_changes():
    global reboot_state
    for i in table.rows:
        if 'create' in i.keys() and i['create']:
            db.add_device(i)
            i['create'] = False
        else:
            db.change_device(i)
    save_btn.set_visibility(False)
    refresh_values()
    reboot_state = True
    table.update()
    print("changes saved")


def remove_devices():
    global reboot_state
    for i in table.selected:
        db.delete_device(i['cluster_id'])
    table.remove_rows(*table.selected)
    refresh_values()
    reboot_state = True


def update_device_pair(e):
    for index, i in enumerate(rows):
        if i['cluster_id'] == e.args['cluster_id']:
            rows[index]['ha_device'] = e.args['ha_device']
            break
    db.change_device(e.args)
    refresh_values()
    select_device_slot.refresh()
    table.update()

def manual_reset():
    ser.write("rst \r".encode('utf-8'))

@ui.refreshable
def select_device_slot():
    table.add_slot('body-cell-ha_device', r'''
            <q-select
                v-model="props.row.ha_device"
                :options="''' + str(devices) + r'''"
                :new-value-mode="add-unique"
                @update:model-value="() => $parent.$emit('device_change', props.row)"
            />
            ''')


with ui.header().classes(replace='row items-center') as header:
    with ui.tabs() as tabs:
        ui.tab('Устройства')
        ui.tab('Настройки')

with ui.footer(value=False) as footer:
    ui.label('Footer')

with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
    ui.button(on_click=footer.toggle, icon='contact_support').props('fab')

with ui.tab_panels(tabs, value='Устройства').classes('w-full'):
    with ui.tab_panel('Устройства'):
        with ui.table(row_key='cluster_id', title='Устройства', selection='multiple', columns=columns, rows=rows,
                      pagination=10).classes('w-256') as table:
            with table.add_slot('top-right'):
                with ui.input(placeholder='Search').props('type=search').bind_value(table, 'filter').add_slot('append'):
                    ui.icon('search')
            select_device_slot()
            table.add_slot('body-cell-status', '''
                <q-td key="status" :props="props">
                    <q-badge :color="props.value == false ? 'red' : 'green'">
                        {{ props.value == false ? 'выключен' : 'включен' }}
                    </q-badge>
                </q-td>
            ''')
            table.add_slot('body-cell-enabled', '''
                            <q-td key="enabled" :props="props">
                    <q-toggle v-model="props.row.enabled"  @update:model-value=" $parent.$emit('edit_activate', props.row)" :value="props.row.enabled"/>
                </q-td>
            ''')
            table.on('edit_activate', change_activation_state)
            table.on('device_change', update_device_pair)
            with table.add_slot('bottom-row'):
                with table.cell():
                    add_btn = ui.button(on_click=lambda: add_device(), icon='add').props('flat fab-mini')
                with table.cell():
                    cluster_id = ui.input('Номер канала',
                                          validation={'Поле должно быть заполнено': lambda value: len(value) > 0,
                                                      'Допустимо только числовое значение': lambda
                                                          value: value.isdigit(),
                                                      'Значение должно быть менее 240': lambda value: int(value) < 240})
                with table.cell():
                    ha_device = ui.select(devices, label='Устройство', with_input=True,
                                          validation={'Поле должно быть заполнено': lambda value: value is not None,
                                                      'Выбранное устройство уже используется': lambda
                                                          value: value not in getSelectedDevices()})
                with table.cell():
                    update_btn = ui.button("Обновить список устройств",on_click=lambda: get_devices_ha())
        ui.button('Удалить', on_click=lambda: remove_devices()) \
            .bind_visibility_from(table, 'selected', backward=lambda val: bool(val))
        save_btn = ui.button('Сохранить', on_click=lambda: save_changes())
        save_btn.set_visibility(False)
    with ui.tab_panel('Настройки'):
        ui.label("Отладочная консоль")
        log = ui.log(1000)
        ui.input('Send command').on('keydown.enter', lambda e: (
        ser.write(f'{e.sender.value}\n'.encode()),
            e.sender.set_value(''),
        ))
        ui.button("Перазгрузка ESP",on_click=lambda: manual_reset())

connect_ws()
threading.Thread(target=ping_ws, daemon=True).start()
get_devices_ha()
threading.Thread(target=background_worker, daemon=True).start()
ui.run(host='0.0.0.0', port=3005, binding_refresh_interval=0.1, reload=False, proxy_headers=True,
       forwarded_allow_ips="*")
