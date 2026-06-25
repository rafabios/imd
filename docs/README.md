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

## Antes de publicar

Troque estes links em `docs/index.html` pelo repositorio real:

```txt
https://github.com/rafabios/imd/releases/latest
https://github.com/rafabios/imd
```

Depois que a primeira release com MSI existir, o botao de download vai mandar para o instalador mais recente.
