import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime, timedelta

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context_desktop = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            record_video_dir="artifacts/videos"
        )
        page_desktop = await context_desktop.new_page()

        page_desktop.on("console", lambda msg: print(f"Console: {msg.text}"))
        page_desktop.on("pageerror", lambda err: print(f"Error: {err.message}"))

        # We need a dialog handler to accept prompts automatically
        page_desktop.on("dialog", lambda dialog: asyncio.create_task(dialog.accept("prompt text" if dialog.type == "prompt" else "")))

        print("Navigating to pc.html...")
        await page_desktop.goto("http://localhost:8080/pc.html")
        await page_desktop.wait_for_timeout(2000)

        # 1. Autenticación
        print("Authenticating SuperAdmin...")
        await page_desktop.fill("#usuario", "enfer.ro.98@gmail.com")
        await page_desktop.fill("#password", "enfer1998")
        await page_desktop.click("#btn-ingreso")
        await page_desktop.wait_for_timeout(4000)

        # 3. Gestión de Clientes
        print("Phase 1.3: Gestión de Clientes y Licencias (v-licencias)")
        await page_desktop.evaluate("cambiarVista('v-licencias', document.querySelectorAll('#pantalla-admin .sidebar-nav li')[1]); cargarClientes();")
        await page_desktop.wait_for_timeout(2000)

        # Edit limit
        await page_desktop.evaluate("""
            const row = Array.from(document.querySelectorAll('#tb-clientes tr')).find(tr => tr.innerText.includes('ferrodriguez441@gmail.com'));
            if(row) row.querySelector('button[onclick*="abrirEdicion"]').click();
        """)
        await page_desktop.wait_for_timeout(1000)

        # Ensure modal is visible before filling
        await page_desktop.evaluate("document.getElementById('modal-editar').classList.remove('oculto');")
        await page_desktop.evaluate("document.getElementById('modal-editar').style.display = 'flex';")
        await page_desktop.wait_for_timeout(500)

        await page_desktop.fill("#e-limite-ops", "10", force=True)
        await page_desktop.fill("#e-limite-own", "2", force=True)
        await page_desktop.evaluate("guardarEdicion()")
        await page_desktop.wait_for_timeout(2000)

        # Renovar
        new_date = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
        await page_desktop.evaluate(f"""
            const row = Array.from(document.querySelectorAll('#tb-clientes tr')).find(tr => tr.innerText.includes('ferrodriguez441@gmail.com'));
            if(row) {{
                const input = row.querySelector('input[type="date"]');
                input.value = '{new_date}';
                row.querySelector('button[onclick*="actualizarVencimiento"]').click();
            }}
        """)
        await page_desktop.wait_for_timeout(2000)

        # Ver equipo
        await page_desktop.evaluate("""
            const row = Array.from(document.querySelectorAll('#tb-clientes tr')).find(tr => tr.innerText.includes('ferrodriguez441@gmail.com'));
            if(row) row.querySelector('button[onclick*="verEquipo"]').click();
        """)
        await page_desktop.wait_for_timeout(2000)
        await page_desktop.screenshot(path="artifacts/screenshots/F1_03_ver_equipo.png")

        # close modal
        await page_desktop.evaluate("cerrarModal('modal-equipo')")
        await page_desktop.wait_for_timeout(1000)

        # 4. Importación Masiva Inteligente de Rodeo
        print("Phase 1.4: Importación Masiva")
        await page_desktop.evaluate("cambiarVista('v-masiva', document.querySelectorAll('#pantalla-admin .sidebar-nav li')[2]); cargarClientesMasiva();")
        await page_desktop.wait_for_timeout(2000)

        # Create CSV
        csv_content = "Caravana,Categoria,Peso,Fecha,Lote,Raza\nJULES-01,Novillo,385.5,2026-09-01,Invernada A,Nelore\nJULES-02,Vaca,420.0,2026-09-01,Cría General,Brangus\nJULES-03,Ternero,160.0,2026-09-01,Destete,Braford"
        with open("artifacts/import_data.csv", "w") as f:
            f.write(csv_content)

        await page_desktop.select_option("#sel-cliente-masiva", value="ferrodriguez441@gmail.com", force=True)
        await page_desktop.wait_for_timeout(1000)

        await page_desktop.set_input_files("#archivo-excel", "artifacts/import_data.csv")
        await page_desktop.wait_for_timeout(2000)

        # click button to parse it
        await page_desktop.evaluate("leerArchivoInteligente()")
        await page_desktop.wait_for_timeout(2000)

        # map columns
        await page_desktop.select_option("#map-caravana", label="Caravana", force=True)
        await page_desktop.select_option("#map-categoria", label="Categoria", force=True)
        await page_desktop.select_option("#map-peso", label="Peso", force=True)
        await page_desktop.select_option("#map-fecha", label="Fecha", force=True)
        await page_desktop.select_option("#map-lote", label="Lote", force=True)
        await page_desktop.select_option("#map-raza", label="Raza", force=True)

        await page_desktop.evaluate("procesarMapeoEInyectar()")
        await page_desktop.wait_for_timeout(4000)

        await page_desktop.screenshot(path="artifacts/screenshots/F1_04_carga_masiva_exitosa.png")

        print("Phase 1.5: Edición Masiva y Purgas en Firestore (v-editar-masiva)")
        await page_desktop.evaluate("cambiarVista('v-editar-masiva', document.querySelectorAll('#pantalla-admin .sidebar-nav li')[3]); inicializarModuloEditarMasiva();")
        await page_desktop.wait_for_timeout(1000)

        await page_desktop.select_option("#sel-hacienda-editar", value="ferrodriguez441@gmail.com", force=True)
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.evaluate("cargarEventosCargaMasiva()")
        await page_desktop.wait_for_timeout(3000)

        # find JULES-01 and edit
        await page_desktop.evaluate("""
            const row = Array.from(document.querySelectorAll('#tb-eventos-masivos tr')).find(tr => tr.innerText.includes('JULES-01'));
            if(row) row.querySelector('button[onclick*="abrirModalEditarEvento"]').click();
        """)
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.evaluate("document.getElementById('modal-editar-evento').style.display = 'flex';")
        await page_desktop.wait_for_timeout(500)

        await page_desktop.fill("#edit-ev-valor", "390.0", force=True)
        await page_desktop.fill("#edit-ev-detalles", "Modificado por Jules QA", force=True)
        await page_desktop.evaluate("guardarEdicionEventoFirestore()")
        await page_desktop.wait_for_timeout(2000)

        # Cambio de Fecha Masiva de Lote
        await page_desktop.fill("#fecha-cambio-masivo", "2026-09-05T00:00", force=True)
        await page_desktop.evaluate("cambiarFechaMasivaLote()")
        await page_desktop.wait_for_timeout(3000)

        print("Phase 1.6: Control Global del Sistema y Kill Switch (v-config)")
        await page_desktop.evaluate("cambiarVista('v-config', document.querySelectorAll('#pantalla-admin .sidebar-nav li')[4]); checkStatusInicial();")
        await page_desktop.wait_for_timeout(1000)

        await page_desktop.fill("#txt-aviso-mant", "⚠️ MANTENIMIENTO PROGRAMADO EN 30 MINUTOS", force=True)
        await page_desktop.evaluate("enviarAvisoMantenimiento()")
        await page_desktop.wait_for_timeout(2000)

        # Kill switch on
        await page_desktop.evaluate("toggleMantenimiento('ON')")
        await page_desktop.wait_for_timeout(2000)

        # Kill switch off
        await page_desktop.evaluate("toggleMantenimiento('OFF')")
        await page_desktop.wait_for_timeout(2000)

        print("--- PHASE 2 ---")
        # 1. Verificación de Rodeo Completo e Integridad del Dashboard
        # Cierra sesión e ingresa con ferrodriguez441@gmail.com / 123456.
        await page_desktop.evaluate("cerrarSesion()")
        await page_desktop.wait_for_timeout(2000)

        print("Authenticating Propietario Ganadero...")
        await page_desktop.fill("#usuario", "ferrodriguez441@gmail.com")
        await page_desktop.fill("#password", "123456")
        await page_desktop.click("#btn-ingreso")
        await page_desktop.wait_for_timeout(5000)

        await page_desktop.screenshot(path="artifacts/screenshots/F2_01_dashboard_completo.png")

        # 2. Personalización del Dashboard
        print("Phase 2.2: Personalización del Dashboard")
        await page_desktop.evaluate("cambiarVista('v-config', document.querySelectorAll('#sidebar .sidebar-nav li')[4])")
        await page_desktop.wait_for_timeout(1000)

        # uncheck graficos
        await page_desktop.evaluate("""
            const checkboxes = document.querySelectorAll('.chk-graf');
            if (checkboxes.length > 2) {
                checkboxes[0].checked = false;
                checkboxes[1].checked = false;
            }
            verificarLimiteGraficos(checkboxes[0]);
        """)
        await page_desktop.wait_for_timeout(2000)
        await page_desktop.evaluate("cambiarVista('v-dash', document.querySelectorAll('#sidebar .sidebar-nav li')[0]); procesarDatosDashboard();")
        await page_desktop.wait_for_timeout(2000)

        await page_desktop.evaluate("cambiarVista('v-config', document.querySelectorAll('#sidebar .sidebar-nav li')[4])")
        await page_desktop.wait_for_timeout(1000)

        # check graficos
        await page_desktop.evaluate("""
            const checkboxes = document.querySelectorAll('.chk-graf');
            if (checkboxes.length > 2) {
                checkboxes[0].checked = true;
                checkboxes[1].checked = true;
            }
            verificarLimiteGraficos(checkboxes[0]);
        """)
        await page_desktop.wait_for_timeout(2000)
        await page_desktop.evaluate("cambiarVista('v-dash', document.querySelectorAll('#sidebar .sidebar-nav li')[0]); procesarDatosDashboard();")
        await page_desktop.wait_for_timeout(2000)

        print("Phase 2.3: Manga / Brete")
        await page_desktop.evaluate("cambiarVista('v-ficha', document.querySelectorAll('#sidebar .sidebar-nav li')[1])")
        await page_desktop.wait_for_timeout(1000)

        # Buscar JULES-01
        await page_desktop.fill("#buscador-caravana", "JULES-01", force=True)
        await page_desktop.evaluate("buscarCaravanaBtn()")
        await page_desktop.wait_for_timeout(2000)

        # modal-peso
        await page_desktop.evaluate("document.getElementById('modal-peso').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.fill("#i-peso-val", "435.0", force=True)
        await page_desktop.select_option("#i-peso-cond", label="CC 3.5 (Buena Cobertura)", force=True)
        await page_desktop.fill("#i-peso-txt", "Control mensual brete", force=True)
        await page_desktop.evaluate("prepararGuardado('modal-peso', 'Peso')")
        await page_desktop.wait_for_timeout(2000)

        # Buscar JULES-02
        await page_desktop.fill("#buscador-caravana", "JULES-02", force=True)
        await page_desktop.evaluate("buscarCaravanaBtn()")
        await page_desktop.wait_for_timeout(2000)

        # modal-diagnostico
        await page_desktop.evaluate("document.getElementById('modal-diagnostico').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.select_option("#i-dx-sel", value="Preñada", force=True)
        await page_desktop.select_option("#i-dx-meses", value="3", force=True)
        await page_desktop.evaluate("prepararGuardado('modal-diagnostico', 'Diagnóstico')")
        await page_desktop.wait_for_timeout(2000)

        # modal-inseminacion
        await page_desktop.evaluate("document.getElementById('modal-inseminacion').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.fill("#i-ins-toro", "TORO-DON-PEDRO - PAJ-9821", force=True)
        await page_desktop.select_option("#i-ins-quien", value="IATF", force=True)
        await page_desktop.fill("#i-ins-txt", "Inseminador: Dr. González", force=True)
        await page_desktop.evaluate("prepararGuardado('modal-inseminacion', 'Inseminación')")
        await page_desktop.wait_for_timeout(2000)

        # Buscar JULES-01
        await page_desktop.fill("#buscador-caravana", "JULES-01", force=True)
        await page_desktop.evaluate("buscarCaravanaBtn()")
        await page_desktop.wait_for_timeout(2000)

        # modal-sanidad
        await page_desktop.evaluate("document.getElementById('modal-sanidad').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.select_option("#i-sani-sel", value="OTRO", force=True)
        await page_desktop.fill("#sani-otro", "Ivermectina 3.15%", force=True)
        await page_desktop.fill("#i-sani-txt", "Dosis: 8ml", force=True)
        await page_desktop.evaluate("prepararGuardado('modal-sanidad', 'Sanidad')")
        await page_desktop.wait_for_timeout(2000)

        # modal-nutricion (suponiendo id)
        await page_desktop.evaluate("document.getElementById('modal-nut').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.select_option("#i-nut-prod", value="OTRO", force=True)
        await page_desktop.fill("#nut-otro", "Sal Mineralizada Proteica", force=True)
        await page_desktop.fill("#i-nut-rac", "250 g/animal/día", force=True)
        await page_desktop.fill("#i-nut-txt", "Lote: Invernada A", force=True)
        await page_desktop.evaluate("prepararGuardado('modal-nut', 'Nutrición')")
        await page_desktop.wait_for_timeout(2000)

        # modal-confinamiento
        await page_desktop.evaluate("document.getElementById('modal-confinamiento').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.fill("#i-conf-corral", "Corral 4 - Terminación", force=True)
        await page_desktop.select_option("#i-conf-dieta", value="OTRO", force=True)
        await page_desktop.fill("#i-conf-txt", "Ingreso: 435 Kg | Meta: 520 Kg | Dieta: Silo + Maíz 80/20", force=True)
        await page_desktop.evaluate("prepararGuardado('modal-confinamiento', 'Confinamiento')")
        await page_desktop.wait_for_timeout(2000)

        # modal-perfil
        await page_desktop.evaluate("document.getElementById('m-perfil').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.fill("#f-raza", "Nelore Mocho", force=True)
        await page_desktop.fill("#f-nacimiento", "2024-03", force=True) # YYYY-MM based on type=month
        await page_desktop.fill("#f-padre", "GRAN-CAMPEON-2022 / RP-MATRIZ-450", force=True)
        await page_desktop.evaluate("""
            const fRaza = document.getElementById('f-raza') ? document.getElementById('f-raza').value : "-";
            const fNacimiento = document.getElementById('f-nacimiento') ? document.getElementById('f-nacimiento').value : "-";
            const fPadre = document.getElementById('f-padre') ? document.getElementById('f-padre').value : "-";
            const fMadre = document.getElementById('f-madre') ? document.getElementById('f-madre').value : "-";
            const catValor = document.getElementById('val-categoria') ? document.getElementById('val-categoria').innerText : "-";
            ejecutarAccion('Perfil Master', `${fRaza||"-"}|${fNacimiento||"-"}|${fPadre||"-"}|${fMadre||"-"}`, catValor, 'm-perfil');
        """)
        await page_desktop.wait_for_timeout(2000)

        # modal-clasificacion - ya se maneja en clasificacion rapida u otro
        await page_desktop.evaluate("document.getElementById('modal-clasificacion').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.select_option("#input-cat-rapida", value="Novillos", force=True)
        await page_desktop.fill("#input-carimbo-rapido", "4", force=True)
        await page_desktop.select_option("#input-lote-rapido", value="OTRO", force=True)
        await page_desktop.fill("#lote-otro", "Invernada A", force=True)
        await page_desktop.evaluate("""
            let cat = document.getElementById('input-cat-rapida').value;
            let lote = document.getElementById('input-lote-rapido').value || "-";
            let potrero = document.getElementById('input-potrero-rapido') ? document.getElementById('input-potrero-rapido').value.trim() : "";
            let carimbo = document.getElementById('input-carimbo-rapido').value || "-";
            let detLote = `Lote: ${lote}` + (potrero ? ` | Potrero: ${potrero}` : "");
            ejecutarAccion('Actualización de Datos', `Cat: ${cat} | Carimbo: ${carimbo}`, detLote, 'modal-clasificacion');
        """)
        await page_desktop.wait_for_timeout(2000)

        # modal-comentario
        await page_desktop.evaluate("document.getElementById('modal-comentario').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.fill("#f-comentario-txt", "Animal dócil, excelente respuesta a la ración", force=True)
        await page_desktop.evaluate("prepararGuardado('modal-comentario', 'Comentario')")
        await page_desktop.wait_for_timeout(2000)

        # Buscar JULES-03
        await page_desktop.fill("#buscador-caravana", "JULES-03", force=True)
        await page_desktop.evaluate("buscarCaravanaBtn()")
        await page_desktop.wait_for_timeout(2000)

        # Renombrar Caravana
        await page_desktop.evaluate("document.getElementById('modal-renombrar').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.fill("#f-nueva-caravana", "JULES-03-RENOMBRADO", force=True)
        await page_desktop.evaluate("""
            const n = document.getElementById('f-nueva-caravana').value.trim();
            if(!n || n === rpActivo) { alert("Número inválido."); }
            else {
                ejecutarAccion('Cambio de Caravana', n, `Renombrado`, 'modal-renombrar');
                document.getElementById('f-nueva-caravana').value = '';
                setTimeout(() => { rpActivo = n; buscarCaravanaBtn(n); }, 300);
            }
        """)
        await page_desktop.wait_for_timeout(2000)

        # Buscar JULES-VENTA (crear o usar otro)
        await page_desktop.fill("#buscador-caravana", "JULES-01", force=True)
        await page_desktop.evaluate("buscarCaravanaBtn()")
        await page_desktop.wait_for_timeout(2000)

        # Salida Comercial / Venta
        await page_desktop.evaluate("document.getElementById('modal-venta').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.select_option("#i-venta-tipo", value="Venta Frigorífico / Faena", force=True)
        await page_desktop.fill("#i-venta-destino", "Frigorífico Concepción - Faena Exportación", force=True)
        await page_desktop.fill("#i-venta-txt", "14.500 Gs/Kg", force=True)
        await page_desktop.evaluate("prepararGuardado('modal-venta', 'Venta')")
        await page_desktop.wait_for_timeout(2000)

        # Buscar JULES-02
        await page_desktop.fill("#buscador-caravana", "JULES-02", force=True)
        await page_desktop.evaluate("buscarCaravanaBtn()")
        await page_desktop.wait_for_timeout(2000)

        # Mortandad
        await page_desktop.evaluate("document.getElementById('m-baja').style.display = 'flex';")
        await page_desktop.wait_for_timeout(1000)
        await page_desktop.select_option("#i-baja-causa", value="OTRO", force=True)
        await page_desktop.fill("#baja-otro", "Picadura de Serpiente / Ofidismo", force=True)
        await page_desktop.evaluate("prepararGuardado('m-baja', 'Baja')")
        await page_desktop.wait_for_timeout(2000)

        await page_desktop.screenshot(path="artifacts/screenshots/F2_02_ficha_animal_completa.png")

        # 4. Creación de Operador / Peón de Campo
        print("Phase 2.4: Creación de Operador")
        await page_desktop.evaluate("cambiarVista('v-config', document.querySelectorAll('#sidebar .sidebar-nav li')[4])")
        await page_desktop.wait_for_timeout(1000)

        await page_desktop.fill("#op-nombre", "Peon Jules QA", force=True)
        await page_desktop.fill("#op-usu", "peon_jules", force=True)
        await page_desktop.fill("#op-pass", "123456", force=True)

        # Checkboxes
        await page_desktop.evaluate("""
            const chk = document.querySelectorAll('.chk-permiso');
            if (chk.length >= 4) {
                chk[0].checked = false; // Dashboard
                chk[1].checked = true;  // Manga
                chk[2].checked = true;  // Registro
                chk[3].checked = false; // Informes
            }
        """)
        await page_desktop.evaluate("crearOperador()")
        await page_desktop.wait_for_timeout(4000)

        await page_desktop.screenshot(path="artifacts/screenshots/F2_03_operador_creado.png")

        # Phase 4: Auditoría del Centro de Informes
        print("Phase 4: Centro de Informes")
        await page_desktop.evaluate("cambiarVista('v-reporte', document.querySelectorAll('#sidebar .sidebar-nav li')[3]); actualizarInformeAvanzado();")
        await page_desktop.wait_for_timeout(1000)

        try:
            await page_desktop.evaluate("""
                const sel = document.getElementById('f-inf-modo');
                if(sel) { sel.value = "pesajes"; sel.dispatchEvent(new Event('change')); }
            """)
            await page_desktop.wait_for_timeout(1000)
            await page_desktop.evaluate("ejecutarDescargaPDF()")
            await page_desktop.wait_for_timeout(3000)

            await page_desktop.evaluate("""
                const sel = document.getElementById('f-inf-modo');
                if(sel) { sel.value = "inventario"; sel.dispatchEvent(new Event('change')); }
            """)
            await page_desktop.wait_for_timeout(1000)
            await page_desktop.evaluate("ejecutarDescargaPDF()")
            await page_desktop.wait_for_timeout(3000)

            await page_desktop.evaluate("""
                const sel = document.getElementById('f-inf-modo');
                if(sel) { sel.value = "bajas"; sel.dispatchEvent(new Event('change')); }
            """)
            await page_desktop.wait_for_timeout(1000)
            await page_desktop.evaluate("ejecutarDescargaPDF()")
            await page_desktop.wait_for_timeout(3000)

            await page_desktop.evaluate("""
                const sel = document.getElementById('f-inf-modo');
                if(sel) { sel.value = "ventas"; sel.dispatchEvent(new Event('change')); }
            """)
            await page_desktop.wait_for_timeout(1000)
            await page_desktop.evaluate("ejecutarDescargaPDF()")
            await page_desktop.wait_for_timeout(3000)

            await page_desktop.evaluate("""
                const sel = document.getElementById('f-inf-modo');
                if(sel) { sel.value = "eventos"; sel.dispatchEvent(new Event('change')); }
            """)
            await page_desktop.wait_for_timeout(1000)
            await page_desktop.evaluate("ejecutarDescargaPDF()")
            await page_desktop.wait_for_timeout(3000)
        except Exception as e:
            print("Error downloading reports: " + str(e))

        # Dossier
        await page_desktop.evaluate("cambiarVista('v-ficha', document.querySelectorAll('#sidebar .sidebar-nav li')[1])")
        await page_desktop.wait_for_timeout(1000)

        await page_desktop.fill("#buscador-caravana", "JULES-01", force=True)
        await page_desktop.evaluate("buscarCaravanaBtn()")
        await page_desktop.wait_for_timeout(2000)
        await page_desktop.evaluate("imprimirDossierDirecto()")
        await page_desktop.wait_for_timeout(4000)

        print("Auditoria finalizada con éxito!")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
