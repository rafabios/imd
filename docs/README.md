# Site estatico do IMD

Esta pasta foi criada para publicar o site em GitHub Pages.

## Como publicar

1. Suba o projeto no GitHub.
2. No repositorio, abra `Settings` > `Pages`.
3. Em `Build and deployment`, escolha `Deploy from a branch`.
4. Selecione a branch principal e a pasta `/docs`.
5. Configure o dominio customizado `imd.vemcompy.tec.br`.

O arquivo `CNAME` ja contem:

```txt
imd.vemcompy.tec.br
```

## Downloads automaticos

O botao principal de download aponta para o instalador guiado:

```txt
https://github.com/rafabios/imd/releases/latest/download/IMD-Insane-Music-Downloader-latest-Setup.exe
```

O botao secundario continua apontando para o MSI:

```txt
https://github.com/rafabios/imd/releases/latest/download/IMD-Insane-Music-Downloader-latest.msi
```

O workflow do GitHub Actions gera copias fixas chamadas `IMD-Insane-Music-Downloader-latest-Setup.exe` e `IMD-Insane-Music-Downloader-latest.msi` junto com os arquivos versionados. Assim o site sempre baixa os instaladores da ultima release sem editar HTML.
