
"use client"; //avisa ao react que vai utilizar os serviços de cliente

import { useState } from "react";
import { Card, Button, TextInput, Title, Text } from "@tremor/react";

/*=================TIPAGEM========================= */
type Documento = {
  id: number;
  nome: string;
  curso: string;
};


/*Pagina e Cabeçalho */
export default function Home() {
  const [documentos, setDocumentos] = useState<Documento[]>([]);
  const [nome, setNome] = useState("");
  const [curso, setCurso] = useState("");

  // CREATE
  function adicionarDocumento() {
    if (!nome || !curso) return;
    const novoDocumento: Documento = { id: Date.now(), nome, curso };
    setDocumentos([...documentos, novoDocumento]);
    setNome("");
    setCurso("");
  }
  //READ?



  
  // UPDATE?



//DELETE
  function deletarDocumento(id: number) {
    setDocumentos(documentos.filter(doc => doc.id !== id));
  }

  return (
    <main className="p-12 bg-slate-50 min-h-screen">
      <div className="max-w-md mx-auto">
        <Card className="p-6 shadow-lg">
          <Title className="text-blue-600">DataCotas - Cadastro</Title>
          <Text className="mb-4">Gerencie os documentos do curso abaixo.</Text>

          <div className="space-y-3">
            <TextInput 
              placeholder="Nome do Aluno" 
              value={nome} 
              onChange={(e) => setNome(e.target.value)} 
            />
            <TextInput 
              placeholder="Nome do Curso" 
              value={curso} 
              onChange={(e) => setCurso(e.target.value)} 
            />
            <Button 
              className="w-full mt-4 bg-blue-600" 
              onClick={adicionarDocumento}
            >
              Adicionar Documento
            </Button>
          </div>
        </Card>

        <div className="mt-8 space-y-4">
          {documentos.map(doc => (
            <Card key={doc.id} className="flex justify-between items-center p-4 border-l-4 border-blue-500">
              <div>
                <Text className="font-bold text-slate-900">{doc.nome}</Text>
                <Text>{doc.curso}</Text>
              </div>
              <Button 
                variant="light" 
                color="red" 
                onClick={() => deletarDocumento(doc.id)}
              >
                Apagar
              </Button>
            </Card>
          ))}
        </div>
      </div>
    </main>
  );
}