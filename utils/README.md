## How to use long description in vote

In order to get around the limitation on the length of metadata, we added the ability to store a description in IPFS network.

Since the IPFS hash is calculated cryptographically, it is protected from modify data.

We recommend adding a Markdown text description to IPFS. To automatically upload a description to IPFS, you can use a helper `upload_vote_description_to_ipfs` function from `utils.ipfs` and provide the result to `create_vote` and `confirm_vote_script` into description_info argument.

Here are examples of supported syntax:

### Special LIDO vote elements
#### Wallets

    `0xf73a1260d222f447210581DDf212D915c09a3249`
[`⚫0xf7...3249`](https://etherscan.io/address/0xf73a1260d222f447210581DDf212D915c09a3249)

#### IPFS hashes

    `bafybeifx7yeb55armcsxwwitkymga5xf53dxiarykms3ygqic223w5sk3m`
[bafy...sk3m](https://bafybeifx7yeb55armcsxwwitkymga5xf53dxiarykms3ygqic223w5sk3m.ipfs.w3s.link/)

### Heading


    # h1 Heading
    ## h2 Heading
    ### h3 Heading
    #### h4 Heading
    ##### h5 Heading
    ###### h6 Heading

# h1 Heading
## h2 Heading
### h3 Heading
#### h4 Heading
##### h5 Heading
###### h6 Heading


### Horizontal Rules
    ___

    ---

    ***
___

---

***


### Emphasis

    **This is bold text**

    __This is bold text__

    *This is italic text*

    _This is italic text_

    ~~Strikethrough~~


**This is bold text**

__This is bold text__

*This is italic text*

_This is italic text_

~~Strikethrough~~


### Blockquotes

    > Blockquotes can also be nested...
    >> ...by using additional greater-than signs right next to each other...
    > > > ...or with spaces between arrows.

> Blockquotes can also be nested...
>> ...by using additional greater-than signs right next to each other...
> > > ...or with spaces between arrows.


### Lists


    + Create a list by starting a line with `+`, `-`, or `*`
    + Sub-lists are made by indenting 2 spaces:
      - Marker character change forces new list start:
        * Ac tristique libero volutpat at
        + Facilisis in pretium nisl aliquet
        - Nulla volutpat aliquam velit
    + Very easy!
Unordered

+ Create a list by starting a line with `+`, `-`, or `*`
+ Sub-lists are made by indenting 2 spaces:
  - Marker character change forces new list start:
    * Ac tristique libero volutpat at
    + Facilisis in pretium nisl aliquet
    - Nulla volutpat aliquam velit
+ Very easy!

Ordered

    1. Lorem ipsum dolor sit amet
    2. Consectetur adipiscing elit
    3. Integer molestie lorem at massa

1. Lorem ipsum dolor sit amet
2. Consectetur adipiscing elit
3. Integer molestie lorem at massa


    1. You can use sequential numbers...
    1. ...or keep all the numbers as `1.


1. You can use sequential numbers...
1. ...or keep all the numbers as `1.`

Start numbering with offset:

    57. foo
    1. bar

57. foo
1. bar


## Code

    Inline `code`

Inline `code`
```
    // Some comments
    line 1 of code
    line 2 of code
    line 3 of code
```
Indented code

    // Some comments
    line 1 of code
    line 2 of code
    line 3 of code


Block code "fences"

    ```
    Sample text here...
    ```
```
Sample text here...
```

### Tables

    | Option | Description |
    | ------ | ----------- |
    | data   | path to data files to supply the data that will be passed into templates. |
    | engine | engine to be used for processing templates. Handlebars is the default. |
    | ext    | extension to be used for dest files. |


| Option | Description |
| ------ | ----------- |
| data   | path to data files to supply the data that will be passed into templates. |
| engine | engine to be used for processing templates. Handlebars is the default. |
| ext    | extension to be used for dest files. |

Right aligned columns

    | Option | Description |
    | ------:| -----------:|
    | data   | path to data files to supply the data that will be passed into templates. |
    | engine | engine to be used for processing templates. Handlebars is the default. |
    | ext    | extension to be used for dest files. |

| Option | Description |
| ------:| -----------:|
| data   | path to data files to supply the data that will be passed into templates. |
| engine | engine to be used for processing templates. Handlebars is the default. |
| ext    | extension to be used for dest files. |


### External Links

[link text](https://vote.lido.fi/)

[link with title](https://vote.lido.fi/ "title text!")

### Images (will be shown as links in vote UI)

    ![lido](https://vote.lido.fi/favicon-1080x1080.svg)
    ![lido](https://vote.lido.fi/favicon-1080x1080.svg "The LIDO VOTE")


![lido](https://vote.lido.fi/favicon-1080x1080.svg)
![lido](https://vote.lido.fi/favicon-1080x1080.svg "The LIDO VOTE")

Like links, Images also have a footnote style syntax

    ![Alt text][id]
![Alt text][id]

With a reference later in the document defining the URL location:

    [id]: https://vote.lido.fi/favicon-1080x1080.svg  "The LIOD"
[id]: https://vote.lido.fi/favicon-1080x1080.svg  "The LIOD"
