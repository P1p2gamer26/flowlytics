import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Camara from "./paginas/Camara";
import Camaras from "./paginas/Camaras";
import Cargar from "./paginas/Cargar";
import Conectar from "./paginas/Conectar";
import Panel from "./paginas/Panel";
import Avisos from "./paginas/Avisos";
import EnVivo from "./paginas/EnVivo";
import { get } from "./api";

type Negocio = { id: number; nombre: string };

export default function App() {
  const [negocio, setNegocio] = useState<number | null>(null);
  const [negocios, setNegocios] = useState<Negocio[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    get<{ business_id: number; negocios: Negocio[] }>("/api/negocio-actual/")
      .then((n) => { setNegocio(n.business_id); setNegocios(n.negocios); })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="p-6">{error}</p>;
  if (negocio === null) return <p className="p-6">Cargando…</p>;

  return (
    <Routes>
      <Route path="/" element={<EnVivo />} />
      <Route path="/panel/" element={<Panel negocio={negocio} negocios={negocios} onCambiarNegocio={setNegocio} />} />
      <Route path="/subir/" element={<Cargar negocio={negocio} />} />
      <Route path="/camaras/" element={<Camaras negocio={negocio} />} />
      <Route path="/camaras/:id/" element={<Camara />} />
      <Route path="/conectar/" element={<Conectar negocio={negocio} />} />
      <Route path="/avisos/" element={<Avisos negocio={negocio} />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
